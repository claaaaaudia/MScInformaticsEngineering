(* ============================== Ficha 4 ============================== *)

(* Using Binary Search Trees as defined in class (see SearchTrees.v) *)

(* ===================================================================== *)

From Stdlib Require Import ZArith.
From Stdlib Require Import Lia.
From Stdlib Require Import List.

Import ListNotations.

Notation "x == y" := (Z.eq_dec x y) (at level 70, no associativity).
Notation "x <?? y" := (Z_lt_ge_dec x y) (at level 70, no associativity).
Notation "x <=?? y" := (Z_le_gt_dec x y) (at level 70, no associativity).
Notation "x >?? y" := (Z_gt_le_dec x y) (at level 70, no associativity).
Notation "x >=?? y" := (Z_ge_lt_dec x y) (at level 70, no associativity).

Set Implicit Arguments.

Open Scope Z_scope.

Definition key := Z.

Inductive tree (A : Type) : Type :=
| Empty
| Node (l : tree A) (k : key) (a : A) (r : tree A).

Arguments Empty {A}.   (*  make the parameter A implicit *)
Arguments Node {A}.

Inductive ForallBT {A : Type} (P: key -> A -> Prop) : tree A -> Prop :=
| Forall_Empty : ForallBT P Empty
| Forall_Node : forall (k: key) (a : A) (l r : tree A),
    P k a -> ForallBT P l -> ForallBT P r -> ForallBT P (Node l k a r).

Hint Constructors ForallBT : core.

(* BST Invariant *)

Inductive BST {A : Type} : tree A -> Prop :=
| BST_Empty : BST Empty
| BST_Node : forall l x v r,
    ForallBT (fun y _ => y < x) l ->
    ForallBT (fun y _ => y > x) r ->
    BST l ->
    BST r ->
    BST (Node l x v r).

Hint Constructors BST : core.

(* some functions *)

(* (insert k v t) is the map containing all the bindings of t along
    with a binding of k to v *)

Fixpoint insert {A : Type} (k : key) (a : A) (t : tree A) : tree A :=
  match t with
  | Empty => Node Empty k a Empty
  | Node l x a' r => if k <?? x then Node (insert k a l) x a' r
                    else if k >?? x then Node l x a' (insert k a r)
                         else Node l k a r
  end.

(* (bound k t) tests whether k is bound in t; returns a boolean *)

Fixpoint bound {A : Type} (k : key) (t : tree A) : bool :=
  match t with
  | Empty => false
  | Node l x a r => if k <?? x then bound k l
                   else if k >?? x then bound k r
                        else true
  end. 

(* (lookup d k t) is the value bound to k in t, or is default
    value d if k is not bound in t *)

Fixpoint lookup {A : Type} (d : A) (k : key) (t : tree A) : A :=
  match t with
  | Empty => d
  | Node l x a r => if k <?? x then lookup d k l
                   else if k >?? x then lookup d k r
                        else a
  end.

(* an alternative way to define lookup (without a default value)
   would be to make the functiom codomain to be type option A  *)

Fixpoint lookupBT {A : Type} (k : key) (t : tree A) : option A :=
  match t with
  | Empty => None
  | Node l x a r => if k <?? x then lookupBT k l
                   else if k >?? x then lookupBT k r
                        else Some a
  end.

(* empty_tree contains no bindings. *)

Definition empty_tree {A : Type} : tree A := Empty.

(* ===================================================================== *)

(* Helpful tactics  *)

Ltac destruct_guard :=
  match goal with
  | |- context [ if ?X == ?Y then _ else _ ] => destruct (X == Y)
  | |- context [ if ?X <=?? ?Y then _ else _ ] => destruct (X <=?? Y)
  | |- context [ if ?X <?? ?Y then _ else _ ] => destruct (X <?? Y)
  | |- context [ if ?X >=?? ?Y then _ else _ ] => destruct (X >=?? Y)
  | |- context [ if ?X >?? ?Y then _ else _ ] => destruct (X >?? Y)
  end.

Ltac dall :=
  repeat (simpl; destruct_guard; try lia; auto).
  
(* ===================================================================== *)

(* Exercise 1 *)

Theorem insert_BST_lookup_eq : forall (A : Type) (k : key) (d a : A) (t : tree A),
                               BST t -> lookup d k (insert k a t) = a.
Proof.
  intros.
  induction H.
  dall.
  dall.
Qed.

Theorem insert_BST_lookup_diff : forall (A : Type) (k w: key) (d a : A) (t : tree A),
                                 BST t -> k <> w -> bound w t = true ->
                                 lookup d w (insert k a t) = lookup d w t.
Proof.
  intros.
  induction H.
  dall. dall.
  - apply IHBST1.
    simpl in H1.
    destruct (w <?? x) in H1; try lia.
    assumption.
  - apply IHBST2.
    simpl in H1; destruct (w <?? x) in H1; try lia.
    destruct (w >?? x) in H1; try lia; assumption.
Qed.


(* ===================================================================== *)

(* Exercise 2 *)

Inductive Sorted : list Z -> Prop := 
  | sorted0 : Sorted nil 
  | sorted1 : forall z:Z, Sorted (z :: nil) 
  | sorted2 : forall (z1 z2:Z) (l:list Z), 
        z1 <= z2 -> Sorted (z2 :: l) -> Sorted (z1 :: z2 :: l). 

Fixpoint inorderKeys {A : Type} (t : tree A) : list key :=
  match t with
  | Empty => []
  | Node l k a r => inorderKeys l ++ [k] ++ inorderKeys r
  end.
  
Lemma sorted_app: forall l1 l2 x,
  Sorted l1 -> Sorted l2 ->
  Forall (fun n => n <= x) l1 -> Forall (fun n => n >= x) l2 ->
  Sorted (l1 ++ x :: l2). 
Admitted.
  
Lemma ForallBT_Forall_lt : forall A x t,
    ForallBT (fun (y : key) (_ : A) => y < x) t -> Forall (fun n : Z => n < x) (inorderKeys t).
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl. (*apply Forall_app.*) rewrite Forall_app. split.
    + assumption.
    + constructor; assumption.
Qed.

Lemma ForallBT_Forall_gt : forall A x t,
    ForallBT (fun (y : key) (_ : A) => y > x) t -> Forall (fun n : Z => n > x) (inorderKeys t).
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl. (*apply Forall_app.*) rewrite Forall_app. split.
    + assumption.
    + constructor; assumption.
Qed.
  
Theorem sorted_inorderKeys : forall (A : Type) (t : tree A),
    BST t -> Sorted (inorderKeys t).
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl. apply sorted_app.
    + assumption.
    + assumption.
    + apply Forall_impl with (P := fun n => n < x).
      * intros. lia.
      * apply ForallBT_Forall_lt. assumption.
    + apply Forall_impl with (P := fun n => n > x).
      * intros. lia.
      * apply ForallBT_Forall_gt. assumption.
Qed.