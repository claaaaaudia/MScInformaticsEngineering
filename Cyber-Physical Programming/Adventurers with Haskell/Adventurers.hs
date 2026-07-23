{-# LANGUAGE FlexibleInstances #-}
module Adventurers where

import DurationMonad
import Probability
import ListUtils  
import Data.List (nub, intercalate, sortBy)
import Data.Ord

-- List of adventurers
data Adventurer = P1 | P2 | P5 | P10 deriving (Show,Eq,Enum)

-- Adventurers + the lantern
type Objects = Either Adventurer ()

{-- 
 - State of the game, i.e. the current position of each adventurer
 - + the lantern. The function (const False) represents the initial state of the
 - game, i.e. all adventurers + the lantern on the left side of the bridge.  The
 - function (const True) represents the end state of the game, i.e. all
 - adventurers + the lantern on the right side of the bridge.  
--}
type State = Objects -> Bool

instance Show State where
  show s = (show . (fmap show)) [s (Left P1),
                                 s (Left P2),
                                 s (Left P5),
                                 s (Left P10),
                                 s (Right ())]

instance Eq State where
  (==) s1 s2 = and [s1 (Left P1) == s2 (Left P1),
                    s1 (Left P2) == s2 (Left P2),
                    s1 (Left P5) == s2 (Left P5),
                    s1 (Left P10) == s2 (Left P10),
                    s1 (Right ()) == s2 (Right ())]

-- Initial state of the game
gInit :: State
gInit = const False

-- Changes the state s of the game for a given object o
changeState :: Objects -> State -> State
changeState o s = \x -> if x == o then not (s o) else s x

-- Changes the state of the game for a list of objects 
mChangeState :: [Objects] -> State -> State
mChangeState os s = foldr changeState s os

-- Adventurers
allAdventurers :: [Adventurer]
allAdventurers = [P1, P2, P5, P10]

--- TASK 1 -------------------------------------------------------

-- Time that each adventurer takes to cross the bridge
getTimeAdv :: Adventurer -> Int
getTimeAdv P1 = 1
getTimeAdv P2 = 2
getTimeAdv P5 = 5
getTimeAdv P10 = 10

{-- 
 - For a given state of the game, the function presents 
 - all possible moves that the adventurers can make.  
--}
allValidPlays :: State -> ListDur State
allValidPlays s = manyChoice validGroups
  where
    lanternSide = s (Right ()) -- what side lantern is on
    available = filter (\a -> s (Left a) == lanternSide) allAdventurers -- adventurers on the same side as the lantern
    soloMoves = map (toPlay . singleton) available -- moves with one adventurer
    pairMoves = map (toPlay . pairToList) (makePairs available) -- moves with two adventurers
    validGroups = soloMoves ++ pairMoves -- all valid moves
    
    toPlay group =
      let time     = maximum (map getTimeAdv group) -- maximum time of 2 adventurers
          objects  = map Left group ++ [Right ()] -- objects to move (adventurers + lantern)
          newState = mChangeState objects s -- new state 
      in  LD [Duration (time, newState)] 

{-- 
 - For a given number n and initial state, the function calculates
 - all possible n-sequences of moves that the adventures can make 
--}
exec :: Int -> State -> ListDur State
exec 0 s = return s
exec n s = allValidPlays s >>= exec (n - 1)

-- final state of the game: everyone + lantern on the right
gFinal :: State -> Bool
gFinal s = all (== True) [s (Left P1), s (Left P2), s (Left P5), s (Left P10), s (Right ())]

{-- 
 - Is it possible for all adventurers to be on the other side
 - in <=17 min and not exceeding 5 moves ? 
--}
leq17 :: Bool
leq17 = any (\(Duration (t, s)) -> t <= 17 && gFinal s) (remLD (exec 5 gInit))
leq17check = filter (\(Duration (t,s)) -> t <= 17 && gFinal s) (remLD (exec 5 gInit)) 

{-- Is it possible for all adventurers to be on the other side
 - in < 17 min ? 
--}
l17 :: Bool
l17 = any (\(Duration (t, s)) -> t < 17 && gFinal s) (remLD (exec 5 gInit))

l17n :: Int -> Bool
l17n n = any (\(Duration (t, s)) -> t < 17 && gFinal s) (remLD (exec n gInit))

--- END OF TASK 1 -------------------------------------------------

--- TASK 2 --------------------------------------------------------

-- Represents which adventurer(s) to move next
type Move = Either Adventurer (Adventurer, Adventurer)

prob :: Adventurer -> Dist Int
prob adv = uniform [x `div` 2, x, x + x `div` 2]
  where x = getTimeAdv adv

-- Calculates the resulting state based on which adventurers to move
-- next and their probabilistic crossing times
play :: Move -> State -> DistDur State
play move s = DD (fmap (\t -> Duration (t, newState)) groupTimeDist)
  where
    advs = case move of -- get the adventurer(s) to move
             Left a       -> [a] 
             Right (a, b) -> [a, b]
    objects       = map Left advs ++ [Right ()] -- objects to move (adventurers + lantern)
    newState      = mChangeState objects s -- new state after moving the adventurers
    groupTimeDist = fmap maximum (mapM prob advs) -- distribution of the time taken

-- Extends the previous function to lists of movements
plays :: [Move] -> State -> DistDur State 
plays [] s = return s
plays (m:ms) s = play m s >>= plays ms
 
--- END OF TASK 2 -------------------------------------------------

--- TASK 3 --------------------------------------------------------

---------- Visualisation of the path taken

execWithPath :: Int -> State -> ListDur ([Duration State], State)
execWithPath 0 s = return ([], s)
execWithPath n s = LD $ do
  Duration (t, s') <- remLD (allValidPlays s) -- get the time and new state from the valid plays
  Duration (t', (path, sf)) <- remLD (execWithPath (n-1) s') -- recursively get the path and final state from the remaining moves
  return (Duration (t + t', (Duration (t, s') : path, sf))) -- accumulate the time and path

printPath :: [Duration State] -> IO ()
printPath steps = do
  putStrLn ("Initial: " ++ show gInit)
  mapM_ (\(i, Duration (t, s)) -> -- mapM_ because we want to print each step without accumulating results
    putStrLn ("Step " ++ show i ++ " [+" ++ show t ++ " min]: " ++ show s))
    (zip [1..] steps)

-- Find solutions to leq and print the first one found
printLeq :: Int -> Int -> IO ()
printLeq n t = case solutions of
  [] -> putStrLn "No solution found."
  (Duration (_, (path, _))):_ -> printPath path
  where
    solutions = filter (\(Duration (d, (_, s))) -> d <= t && gFinal s) (remLD (execWithPath n gInit))

---------- Claims in probabilistic setting

-- Full distribution sorted by time
timeDist :: DistDur a -> [(Int, ProbRep)]
timeDist dd =
  let pairs = [(getDuration d, p) | (d, p) <- unD (remDD dd)] -- get the duration and probability pairs from the distribution
      times  = nub (map fst pairs) -- get unique times
      agg t  = (t, sum [p | (t', p) <- pairs, t' == t]) -- aggregate probabilities for each time
  in  sortBy (comparing fst) (map agg times) -- sort by time

-- Probability of finishing in exactly n minutes
probExact :: Int -> DistDur a -> ProbRep
probExact n dd = sum [p | (t, p) <- timeDist dd, t == n]

-- Probability of finishing in less than n minutes
probLessThan :: Int -> DistDur a -> ProbRep
probLessThan n dd = sum [p | (t, p) <- timeDist dd, t < n]

-- Probability of finishing in at most n minutes
probAtMost :: Int -> DistDur a -> ProbRep
probAtMost n dd = sum [p | (t, p) <- timeDist dd, t <= n]

-- Evaluate the two adventurer claims directly
evaluateClaims :: DistDur a -> IO ()
evaluateClaims dd = do
  let dist     = timeDist dd
      pUnder19 = probLessThan 19 dd
      pExact17 = probExact    17 dd
      pUnder17 = probLessThan 17 dd

  putStrLn "Adventurer Claims"
  putStrLn ("P(crossing < 19 min) = " ++ show pUnder19)
  putStrLn ("P(crossing = 17 min) = " ++ show pExact17)
  putStrLn ("P(crossing < 17 min) = " ++ show pUnder17)

optimalMove :: [Move]
optimalMove = [ Right (P1, P2)
               , Left  P1
               , Right (P5, P10)
               , Left  P1
               , Right (P1, P2) ]

--- END OF TASK 3 -------------------------------------------------

--- MONAD IMPLEMENTATIONS -----------------------------------------

-- Non-determinism combined with durations
data ListDur a = LD [Duration a] deriving Show

remLD :: ListDur a -> [Duration a]
remLD (LD x) = x

instance Functor ListDur where
   fmap f = let f' = (fmap f) in
     LD . (map f') . remLD

instance Applicative ListDur where
   pure x = LD [Duration (0,x)]
   l1 <*> l2 = LD $ do x <- remLD l1
                       y <- remLD l2
                       return $ do f <- x; a <- y; return (f a)

instance Monad ListDur where
   return = pure
   l >>= k = LD $ do x <- remLD l
                     g x where
                       g(Duration (i,x)) = let u = (remLD (k x))
                          in map (\(Duration (i',x)) -> Duration (i + i', x)) u

manyChoice :: [ListDur a] -> ListDur a
manyChoice = LD . concat . (map remLD)

-- Probabilistic behaviour combined with durations (note the similarity
-- with the previous code)
data DistDur a = DD (Dist (Duration a)) deriving Show

remDD :: DistDur a -> Dist (Duration a)
remDD (DD x) = x

-- Expose the duration inside a probabilistic duration distribution.
stepDur :: DistDur a -> DistDur (Int, a)
stepDur (DD d) = DD (fmap (\(Duration (t, s)) -> Duration (t, (t, s))) d)

instance Functor DistDur where
        fmap f = DD . (fmap (fmap f)) . remDD

instance Applicative DistDur where
        pure x = DD (return $ return x)
        d1 <*> d2 = DD $ do x <- remDD d1
                            y <- remDD d2
                            return $ do f <- x; a <- y; return (f a)

instance Monad DistDur where
        return = pure
        d >>= k = DD $ do x <- remDD d
                          g x where
                          g(Duration (i,x)) = let u = (remDD (k x))
                                in fmap (\(Duration (i',x)) -> Duration (i + i', x)) u


--- END OF MONAD IMPLEMENTATIONS ----------------------------------

--------- LIST UTILS ----------------------------------------------

makePairs :: (Eq a) => [a] -> [(a,a)]
makePairs as = normalize $ do a1 <- as; a2 <- as; [(a1,a2)]
                                
normalize :: (Eq a) => [(a,a)] -> [(a,a)]
normalize l = removeSw $ filter p1 l where
  p1 (x,y) = if x /= y then True else False

removeSw :: (Eq a) => [(a,a)] -> [(a,a)]
removeSw [] = []
removeSw ((a,b):xs) = if elem (b,a) xs then removeSw xs else (a,b):(removeSw xs)