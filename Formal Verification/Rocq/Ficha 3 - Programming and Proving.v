(* ============================== Ficha 3 ============================== *)

(* Correct-by-construction programming :

   Inductive relation : defines what the function does.
                        has one constructor per base case and one per recursive case
   
   Correctness theorem : defines the function's specification.
                         statement is always 
                              forall inputs, { output | Relation inputs output }
                         proof pattern: 
                              intros. induction (list or natural). base case. inductive case.
   
   then extract the proof and get the verified program :)
 *)

(* ===================================================================== *)

From Stdlib Require Import ZArith.
From Stdlib Require Import Lia.
From Stdlib Require Import List.

(* function that, given natural n and value x, will give a list of n elements
   all equal to x (x repeated n times) *)

Inductive Rep {A:Type} (x:A) : nat -> list A -> Prop :=
| rep0 : Rep x 0 nil
| repS : forall n l, Rep x n l -> Rep x (S n) (cons x l).

(* we want to prove that, for all n and x, there is a list l that satisfies
   the specification (inhabited) *)

Theorem replicate_correct :
  forall (A:Type) (n:nat) (x:A),
    { l:list A | Rep x n l }.
Proof.
  intros A n x.
  induction n.
  - exists nil.
    constructor.
  - destruct IHn as [l Hl].
    exists (cons x l).
    constructor.
    exact Hl.
Qed.

From Stdlib Require Extraction.
Extraction Language Haskell.

Extraction Inline sig_rect.
Extraction Inline list_rect.
Extraction Inline False_rect.

Recursive Extraction replicate_correct.

(* ===================================================================== *)

(* function that receives a list of pairs of naturals and produces the list
   with the sums of each pair *)
   
Inductive PairSum : list (nat * nat) -> list nat -> Prop :=
| ps_nil :
    PairSum nil nil
| ps_cons :
    forall a b l ls,
      PairSum l ls ->
      PairSum (cons (a,b) l) (cons (a + b) ls).
      
(* we want to prove that, for all lists l, there is a list of naturals that
   satisfies the specification (inhabited) *)
   
Theorem pairSum_correct : 
  forall (l : list (nat * nat)),
    { ls : list nat | PairSum l ls }.
Proof.
  intros.
  induction l.
  - exists nil. constructor.
  - destruct a as [x y]. (* decompose pairs, turn a:nat*nat into x,y:nat *)
    destruct IHl as [ls Hls]. (* induction, separate IHl into two *)
    exists (cons (x + y) ls). (* construct the new list with (x+y) at the front *) 
    constructor. (* prove the relation to the extended list *)
    exact Hls. (* it is satisfied *)
Qed.

Recursive Extraction pairSum_correct.

(* ===================================================================== *)

(* given : function that counts the number of occurrences of an integer in a list *)

Notation "x == y" := (Z.eq_dec x y) (at level 70, no associativity).
Fixpoint count (z:Z) (l:list Z) {struct l} : nat :=
  match l with
  | nil => 0%nat
  | (w :: t) => if (z == w)
        then S (count z t)
        else count z t
  end.

Lemma property : forall (x:Z) (a:Z) (l:list Z), x <> a -> count x (a :: l) = count x l.
Proof.
  intros.
  simpl.
  destruct (x == a).
  - contradiction.   (* if took then path *) 
  - reflexivity.     (* if took else path *)
Qed.

(* inductive relation that describes the relation between input and output 
   (count's specification) *)

Inductive Count (z : Z) : list Z -> nat -> Prop :=
| count_nil : Count z nil 0
| count_cons_eq :
    forall a l n, z = a -> Count z l n -> Count z (a :: l) (S n)
| count_cons_noteq :
    forall a l n, z <> a -> Count z l n -> Count z (a :: l) n.

(* proving that it is inhabited *)

Theorem count_correct : forall (z : Z) (l : list Z), { n : nat | Count z l n }.
Proof.
  intros z l.
  induction l.
  - exists 0.
    constructor.
  - destruct IHl as [n Hn].
    destruct (z == a).
    + exists (S n).
      apply count_cons_eq.
      * exact e.
      * exact Hn.
    + exists n.
      apply count_cons_noteq.
      * exact n0.
      * exact Hn.
Qed.
