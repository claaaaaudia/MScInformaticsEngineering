module Game where

import Adventurers
import Control.Monad (unless)
import Data.List (intercalate, nub)
import System.IO (hSetBuffering, stdout, BufferMode(..))

-- A terminal game loop where the user picks which adventurers to move each turn and the terminal shows 
-- the current state after each move, accumulated time, and remaining adventurers

-- Rendering
renderBridge :: State -> Int -> IO ()
renderBridge s elapsed = do
  putStrLn (replicate 50 '-')
  putStrLn ("  Elapsed time : " ++ show elapsed ++ " min")
  putStrLn ("  Lantern      : " ++ if s (Right ()) then "RIGHT" else "LEFT ")
  let fmt xs = if null xs then "(empty)" else intercalate "  " (map show xs)
  putStrLn ("  LEFT: " ++ fmt (filter (not . s . Left) [P1 .. P10]))
  putStrLn   " ~~~~~~~~~~~~~~~~~~~~~~~ BRIDGE ~~~~~~~~~~~~~~~~~~~~~~~ "
  putStrLn ("  RIGHT: " ++ fmt (filter (s . Left) [P1 .. P10]))
  putStrLn (replicate 50 '-')

-- Move parsing with Maybe
parseAdv :: String -> Maybe Adventurer
parseAdv "1"  = Just P1
parseAdv "2"  = Just P2
parseAdv "5"  = Just P5
parseAdv "10" = Just P10
parseAdv _    = Nothing

-- Move validation and state update
parseSelection :: [String] -> Either String [Adventurer]
parseSelection tokens =
  case mapM parseAdv tokens of
    Nothing -> Left "Unknown adventurer. Use: 1  2  5  10"
    Just chosen -> Right chosen

-- Main game loop
gameLoop :: State -> Int -> Int -> IO ()
gameLoop s elapsed moveNum = do
  putStrLn ""
  renderBridge s elapsed
  if gFinal s -- check if all adventurers are on the right
    then do
      putStrLn "Yay! Everyone crossed!"
      putStrLn ("Total time: " ++ show elapsed ++ " min  |  Moves: " ++ show (moveNum - 1))
      putStrLn (replicate 50 '-')
    else do
      let lantern = s (Right ()) -- check side
          avail   = filter (\a -> s (Left a) == lantern) allAdventurers -- check available 
      putStrLn ("Move #" ++ show moveNum)
      putStrLn   "Adventurers who can cross:"
      mapM_ (\a -> putStrLn ("    " ++ show a ++ " (" ++ show (getTimeAdv a) ++ " min)")) avail
      putStrLn "Who crosses? (e.g. '1' or '2 10'):"
      putStr   " > "
      tokens <- words <$> getLine -- get user input and split into tokens
      case parseSelection tokens of
        Left err -> putStrLn err >> gameLoop s elapsed moveNum  -- invalid input
        Right chosen -> do
          let valid = not (null chosen)
                   && length chosen <= 2 -- can only pick 1 or 2 adventurers
                   && length (nub chosen) == length chosen -- must be different
                   && all (`elem` avail) chosen -- must be on the same side as the lantern
          if not valid
            then putStrLn "Pick 1 or 2, with distinct adventurers from the lantern's side."
                 >> gameLoop s elapsed moveNum -- invalid move
            else do
              let time = maximum (map getTimeAdv chosen) -- total time for the move
                  newState = mChangeState (map Left chosen ++ [Right ()]) s -- update state
              putStrLn (intercalate " & " (map show chosen) ++ " cross in " ++ show time ++ " min.")
              gameLoop newState (elapsed + time) (moveNum + 1) 

main :: IO ()
main = do
  hSetBuffering stdout LineBuffering
  putStrLn "Adventurers Game"
  putStrLn "P1=1  P2=2  P5=5  P10=10  (minutes)"
  putStrLn "Optimal: 17 min in 5 moves"
  gameLoop gInit 0 1