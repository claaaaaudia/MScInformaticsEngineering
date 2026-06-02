(* ============================== Ficha 2 ============================== *)

(* Important tactics : 

   inversion : used when we have a hypothesis that is an inductive proposition or 
   an equality and we want to extract information from it. -> refutes the hypothesis
   
   induction : used when we want to prove something by structured induction or an 
   inductive type, generating a subgoal via a constructor. 
                              -> destructs an inductive hypothesis by its constructors
 *)

(* ======================== Functions over lists ======================= *)

(* Proof pattern : 

   1. induction on the list
   2. base case : simpl. reflexivity.
   3. inductive case : simpl. rewrite IH. Search. rewrite.
 *)

From Stdlib Require Import List.

Fixpoint sum (l:list nat) : nat :=
  match l with
  | nil => 0
  | x :: xs => x + sum xs
  end.
  
Compute sum (1::2::3::nil). (* 6 *)
Compute sum (nil). (* 0 *)
Compute sum (4::5::nil). (* 9 *)

Lemma sum1 : forall l1 l2, sum (l1 ++ l2) = sum l1 + sum l2.
Proof.
  intros l1 l2.
  induction l1.
  - simpl. reflexivity.
  - simpl. rewrite IHl1. 
    Search (_ + (_ + _)). 
    rewrite PeanoNat.Nat.add_assoc.
    reflexivity.
Qed.

Lemma sum2 : forall (A:Type) (l:list A), length (rev l) = length l.
Proof.
  intros.
  induction l.
  - simpl. reflexivity.
  - simpl. Search (length (_ ++ _) = _). 
    rewrite last_length.
    rewrite IHl.
    reflexivity.
Qed.

Lemma sum3 : forall (A B:Type) (f:A->B) (l:list A), rev (map f l) = map f (rev l).
Proof.
  intros.
  induction l.
  - simpl. reflexivity.
  - simpl. Search (map _ (_ ++ _)).
    rewrite map_app. 
    rewrite IHl.
    reflexivity.
Qed.

(* ===================== Predicates over lists ======================= *)

(* Proof pattern : 

   To use an In hypothesis : inversion H to case-split on whether it's InHead or InTail
   
   To prove In : apply InHead or InTail explicitly
   
   Combining lists : use destruct on disjunctions, then induction on the In hypothesis itself
 *)

Inductive In {A:Type} (y:A) : list A -> Prop :=
| InHead : forall xs:list A, In y (cons y xs)
| InTail : forall (x:A) (xs:list A), In y xs -> In y (cons x xs).

Check In.

Lemma pred1 : forall (A:Type) (a b : A) (l : list A), In b (a :: l) -> a = b \/ In b l.
Proof.
  intros.
  inversion H.
  - left. reflexivity.
  - right. assumption.
Qed.

Lemma pred2 : forall (A:Type) (l1 l2: list A) (x:A), In x l1 \/ In x l2 -> In x (l1 ++ l2).
Proof.
  intros.
  destruct H as [H1|H2].
  - induction H1.
    + simpl. apply InHead.
    + simpl. apply InTail. assumption.
  - induction l1.
    + simpl. assumption.
    + simpl. apply InTail. assumption.
Qed.

Lemma pred3 : forall (A:Type) (x:A) (l:list A), In x l -> In x (rev l).
Proof.
  intros.
  induction H.
  - simpl. Search (In _ (_ ++ _)). apply pred2. right. apply InHead.
  - simpl. apply pred2. left. exact IHIn.
Qed.

Lemma pred4 : forall (A B:Type) (y:B) (f:A->B) (l:list A), 
                            In y (map f l) -> exists x, In x l /\ y = f x.
Proof.
  intros.
  induction l.
  - simpl in H. inversion H.
  - simpl in H. inversion H as [xs Heq | x xs Htail Heq].
    + exists a. split.
      * apply InHead.
      * reflexivity.
    + apply IHl in Htail.
      destruct Htail as [x0 [Hx0 Hy]].
      exists x0. split.
      * apply InTail. exact Hx0.
      * exact Hy.
Qed.

(* ===================================================================== *)

(* Prefix and Sublist are inductive relations between two lists. The pattern is:

   To prove a Prefix/SubList goal: apply constructors directly (PreNil, PreCons, SLcons1) SLcons2)
   
   To use a Prefix/SubList hypothesis: induction H following the relation's structure
   
   Monotonicity lemmas (like pref1, pref2) always follow : 
          induct on the relation, base case trivial, inductive case uses a Search-found arithmetic lemma
 *)
 
(* =========================== Prefix ================================== *)

Inductive Prefix {A:Type} : list A -> list A -> Prop :=
| PreNil : forall l:list A, Prefix nil l
| PreCons : forall (x:A) (l1 l2:list A), Prefix l1 l2 -> Prefix (x::l1) (x::l2).

Lemma pref1 : forall (A:Type) (l1 l2:list A), Prefix l1 l2 -> length l1 <= length l2.
Proof.
  intros.
  induction H.
  - simpl. Search ( _ <= _). apply le_0_n.
  - simpl. Search ( _ <= _). apply le_n_S. exact IHPrefix.
Qed.

Lemma pref2 : forall l1 l2, Prefix l1 l2 -> sum l1 <= sum l2.
Proof. 
  intros.
  induction H.
  - simpl. apply le_0_n.
  - simpl. Search (_ + _ <= _ + _). apply PeanoNat.Nat.add_le_mono_l. exact IHPrefix.
Qed.

Lemma pref3 : forall (A:Type) (l1 l2:list A) (x:A), (In x l1) /\ (Prefix l1 l2) -> In x l2.
Proof.
  intros A l1 l2 x [Hin Hpref].
  induction Hpref as [l | y l1' l2' Hpref' IH].
  - (* PreNil: l1 = nil, In x nil is impossible *)
    inversion Hin.
  - (* PreCons: l1 = y::l1', l2 = y::l2' *)
    inversion Hin as [xs | z xs Htail].
    + (* InHead: x = y *)
      apply InHead.
    + (* InTail: In x l1' *)
      apply InTail.
      apply IH.
      exact Htail.
Qed.

(* ============================== Sublist ============================== *)

Inductive SubList {A:Type} : list A -> list A -> Prop :=
| SLnil : forall l:list A, SubList nil l
| SLcons1 : forall (x:A) (l1 l2:list A), SubList l1 l2 -> SubList (x::l1) (x::l2)
| SLcons2 : forall (x:A) (l1 l2:list A), SubList l1 l2 -> SubList l1 (x::l2).

Example subl1 : SubList (1::3::nil) (3::1::2::3::4::nil).
Proof.
  apply SLcons2.        (* skip 3 *)
  apply SLcons1.        (* match 1 *)
  apply SLcons2.        (* skip 2 *)
  apply SLcons1.        (* match 3 *)
  apply SLnil.
Qed.

Lemma subl2 : forall (A:Type)(l1 l2 l3 l4:list A),
    SubList l1 l2 -> SubList l3 l4 -> SubList (l1++l3) (l2++l4).
Proof.
  intros A l1 l2 l3 l4 H.
  induction H as [ l              (* SLnil  *)
                 | x l1 l2 _ IH  (* SLcons1 *)
                 | x l1 l2 _ IH  (* SLcons2 *)]; 
  intro Haux.
  - (* SLnil: l1 = nil, l1++l3 = l3, l2++l4 starts with elems of l *)
    simpl.
    (* needs SubList l3 (l++l4)*)
    induction l as [| y l' IHl].
    + simpl. exact Haux.
    + simpl. apply SLcons2. exact IHl.
  - (* SLcons1: l1 = x::l1', l2 = x::l2' *)
    simpl. apply SLcons1. apply IH. exact Haux.
  - (* SLcons2: l2 = x::l2' *)
    simpl. apply SLcons2. apply IH. exact Haux.
Qed.

Lemma subl3 : forall (A:Type)(l1 l2:list A),
    SubList l1 l2 -> SubList (rev l1) (rev l2).
Proof.
  intros A l1 l2 H.
  induction H as [ l
                 | x l1 l2 _ IH
                 | x l1 l2 _ IH ].
  - (* SLnil: rev nil = nil *)
    simpl. apply SLnil.
  - (* SLcons1: rev(x::l1) = rev l1 ++ [x], rev(x::l2) = rev l2 ++ [x] *)
    simpl.
    apply subl2.
    + exact IH.
    + apply SLcons1. apply SLnil.
  - (* SLcons2: rev l2 becomes rev(x::l2) = rev l2 ++ [x] *)
    simpl.
    (* SubList (rev l1) (rev l2 ++ [x]) *)
    (* we got IH : SubList (rev l1) (rev l2) *)
    (* add [x] at the end of bigger list *)
    apply subl2 with (l3 := nil)(l4 := x::nil) in IH.
    + rewrite app_nil_r in IH. exact IH.
    + apply SLnil.
Qed.

Lemma subl4 : forall (A:Type)(x:A)(l1 l2:list A),
    SubList l1 l2 -> In x l1 -> In x l2.
Proof.
  intros A x l1 l2 H.
  induction H as [ l
                 | y l1 l2 _ IH
                 | y l1 l2 _ IH ].
  - (* SLnil: In x nil is False *)
    intro Habs. inversion Habs.
  - (* SLcons1: l1 = y::l1', l2 = y::l2' *)
    intro Hin.
    simpl in Hin. destruct Hin as [Heq | Hin'].
    + simpl. left. exact Heq.   (* Heq : y = x and goal : y = x \/ In x l2 *)
    + simpl. right. apply IH. exact Hin'.
  - (* SLcons2: l2 = y::l2' *)
    intro Hin.
    simpl. right. apply IH. exact Hin.
Qed.