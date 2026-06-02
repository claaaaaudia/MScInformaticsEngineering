(* ================================================================== *)
(* ======================= Sorting a list =========================== *)
(* ================================================================== *)

From Stdlib Require Import ZArith.
From Stdlib Require Import Lia.
From Stdlib Require Import List.

Notation "x == y" := (Z.eq_dec x y) (at level 70, no associativity).
Notation "x <?? y" := (Z_lt_ge_dec x y) (at level 70, no associativity).

Set Implicit Arguments.

Open Scope Z_scope.

(* Sorted predicate over lists of integers *)
Inductive Sorted : list Z -> Prop := 
  | sorted0 : Sorted nil 
  | sorted1 : forall z:Z, Sorted (z :: nil) 
  | sorted2 : forall (z1 z2:Z) (l:list Z), 
        z1 <= z2 -> Sorted (z2 :: l) -> Sorted (z1 :: z2 :: l). 

Fixpoint count (z:Z) (l:list Z) {struct l} : nat :=
  match l with
  | nil => 0%nat   (* %nat to force interpretation in nat, since have we opened Z_scope *)
  | z' :: l' => if z == z' then S (count z l') else  count z l'
  end.

(* The permutation predicate over lists of integers *)
Definition Perm (l1 l2:list Z) : Prop :=  forall z, count z l1 = count z l2.

(*
 Exercise: prove that Perm is an equivalence relation (i.e. is reflexive, symmetric and transitive)
*)

Lemma Perm_reflex : forall l:list Z, Perm l l.
Proof.
  intro.
  unfold Perm.
  reflexivity.
Qed.

Lemma Perm_sym : forall l1 l2, Perm l1 l2 -> Perm l2 l1.
Proof. 
  unfold Perm.
  intros.
  symmetry.
  generalize z. 
  assumption.
Qed.

Lemma Perm_trans : forall l1 l2 l3, Perm l1 l2 -> Perm l2 l3 -> Perm l1 l3.
Proof.
  intros.
  unfold Perm in *.
  intros.
  rewrite H.
  apply H0.
  (*
    ou
    
    generalize z.
    assumption.
  *)
Qed.

Print Perm_trans.
Print eq_trans.

(*  some more lemmas about Perm *)

Lemma Perm_cons : forall a l1 l2, Perm l1 l2 -> Perm (a::l1) (a::l2).
Proof.
  unfold Perm. intros. simpl.
  elim (z == a); try auto.
Qed.

(*  Exercise *)
Lemma Perm_cons_cons : forall x y l, Perm (x::y::l) (y::x::l).
Proof.
  unfold Perm. simpl. intros. destruct (z == x).
  - destruct (z == y); reflexivity.
  - destruct (z == y); reflexivity.
Qed.

(* defining the isort funtion *)

Fixpoint insert (x:Z) (l:list Z) {struct l} : list Z :=
  match l with
  | nil => cons x nil
  | h :: t => if (x <?? h) then cons x (cons h t)
                             else cons h (insert x t)
  end.

Fixpoint isort (l:list Z) : list Z :=
  match l with
  | nil => nil
  | h :: t => insert h (isort t)
  end.

Print isort.

(* prospective proof attempt that isort is correct *)
Theorem isort_correct : forall (l l':list Z), l'=isort l -> Perm l l' /\ Sorted l'.
Proof.
  induction l; intros.
  - unfold Perm; rewrite H; split; auto. simpl. constructor.
  - simpl in H.
    rewrite H.                  (* ??????????? *)
    pose proof (IHl (isort l)) as H1.  specialize (H1 eq_refl).
Abort.

(* some usefull lemmas about count *)

Lemma count_insert_eq : forall x l,
                        count x (insert x l) = S (count x l).
Proof.
  induction l.
  - simpl. destruct (x == x).
    + reflexivity.
    + destruct n. reflexivity.
  - simpl insert. destruct (x <?? a).
    + simpl. destruct (x == x).
      * reflexivity.
      * easy.
    + simpl. destruct (x ==a).
      * rewrite IHl. reflexivity.
      * assumption.
Qed.

Lemma count_cons_diff : forall z x l, z <> x -> count z l = count z  (x :: l).
Proof.
  intros. induction l.
  - simpl. destruct (z == x); easy.
  - simpl. destruct (z == a).
    + destruct (z == x); easy.
    + destruct (z == x); easy.
Qed.

(* Exercise *)
Lemma count_insert_diff : forall z x l, z <> x -> count z l = count z (insert x l).
Proof.
  intros. induction l.
  - simpl. destruct (z == x).
    + contradiction.
    + reflexivity.
  - simpl. destruct (x <?? a).
    + simpl. destruct (z == x).
      * contradiction.
      * destruct (z == a); reflexivity.
    + simpl. destruct (z == a).
      * rewrite IHl. reflexivity.
      * exact IHl.
Qed.

(* the two auxiliary lemmas *)

Lemma insert_Perm : forall x l, Perm (x::l) (insert x l).
Proof. 
  unfold Perm; induction l.
  - simpl. reflexivity.
  - intros. simpl insert. destruct (x <?? a).
    + reflexivity.
    + simpl. destruct (z == x).
      * rewrite e. destruct (x == a); rewrite count_insert_eq; reflexivity.
      * destruct (z == a). 
        **  f_equal. apply count_insert_diff. assumption.
        ** apply count_insert_diff. assumption.
Qed.

Lemma insert_Sorted : forall x l, Sorted l -> Sorted (insert x l). 
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl. destruct (x <?? z).
    + apply sorted2. lia. constructor.
    + apply sorted2. lia. constructor.
  - simpl. destruct (x <?? z1).
    + apply sorted2. lia. apply sorted2. lia. exact H0.
    + destruct (x <?? z2).
      * apply sorted2. lia. apply sorted2. lia. exact H0.
      * apply sorted2. exact H. 
        simpl in IHSorted. destruct (x <?? z2).
        -- lia.
        -- exact IHSorted.
Qed.

(* the proof that isort is correct *)
Theorem isort_correct : forall (l l':list Z), l'=isort l -> Perm l l' /\ Sorted l'.
Proof.
  induction l; intros.
  - unfold Perm; rewrite H; split; auto. simpl. constructor.
  - simpl in H.
    rewrite H.                  (* ??????????? *)
    destruct (IHl (isort l)).   (* Exercise: complete the proof *)
      + reflexivity.
      + split.
        * unfold Perm. intros. simpl. destruct (z==a). subst.
          -- rewrite count_insert_eq. f_equal. unfold Perm in H0. apply H0.
          -- unfold Perm in H0. rewrite H0. Search count.
             apply count_insert_diff. assumption.
        * apply insert_Sorted. assumption.
Qed.

(* ==================================================================== *)
(* Instead of this approach, we can give a "strong specification" of a
   function  (using specification types), and extract the function from 
   its proof (the prove that the specification is inhabited).
*)

From Stdlib Require Extraction.

(* EXTRACTION *) 
(* using specification types *)
Lemma count_insert_same : forall x l, S (count x l) = count x (insert x l).
Proof.
  intros. induction l.
  - simpl. destruct (x == x).
    + reflexivity.
    + contradiction.
  - simpl. destruct (x <?? a).
    + simpl. destruct (x == x).
      * reflexivity.
      * contradiction.
    + simpl. destruct (x == a).
      * rewrite IHl. reflexivity.
      * exact IHl.
Qed.

Definition inssort : forall (l:list Z), { l' | Perm l l' & Sorted l' }.
Proof.
  induction l.
  - exists nil.
    + unfold Perm. intro. reflexivity.
    + constructor.
  - elim IHl. intros l1 Hperm Hsorted. exists (insert a l1).
    + unfold Perm. intro z. simpl.
      destruct (z == a).
      * subst. rewrite <- count_insert_same. 
        unfold Perm in Hperm. rewrite Hperm. reflexivity.
      * rewrite <- count_insert_diff.
        -- unfold Perm in Hperm. rewrite Hperm. reflexivity.
        -- exact n.
    + apply insert_Sorted. exact Hsorted.
Qed.

Extraction Language Haskell.
Recursive Extraction inssort.

Extraction Inline list_rec.
Extraction Inline list_rect.
Extraction Inline sig2_rec.
Extraction Inline sig2_rect.

Extraction inssort.
Recursive Extraction inssort.