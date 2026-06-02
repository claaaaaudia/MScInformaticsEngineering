Set Warnings "-notation-overridden,-parsing,-deprecated-hint-without-locality".

(* ================================================================= *)
(* ====================== Binary Search Trees ====================== *)
(* ================================================================= *)

From Stdlib Require Import String.  (* just for an example *)

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

(* A Binary Search Tree (BST) is a type of binary tree data structure used
   to store elements in a way that keeps them ordered.

   A BST is a bynary tree that obey the following invariant: for any non-empty node,
   - left subtree keys < node key
   - right subtree keys > node key

   This ordering allows efficient search, insertion, and deletion.
   BST are well suited to implement maps in a more efficient way than in lists.
 
   We define a polimorphic inductive datatype tree A, which is
   a binary tree of pairs (key,value). We use the type Z as the key type,
   since it has convinient total order.
 *)

Definition key := Z.

(* Empty is the empty tree, and each Node stores a mapping from a key to a value,
   along with the left and right subtrees.
*)

Inductive tree (A : Type) : Type :=
| Empty
| Node (l : tree A) (k : key) (a : A) (r : tree A).

Arguments Empty {A}.   (*  make the parameter A implicit *)
Arguments Node {A}.

(* This defines a binary tree but there, but the BST invariant is not part of
   the definition of tree.
   Let's formalize the BST invariant:
   - An empty tree is a BST.
   - A non-empty tree is a BST if all its left nodes have a lesser key,
     its right nodes have a greater key,
     and the left and right subtrees are themselves BSTs.
 *)

(* First, we define a helper ForallT predicate to express that idea that
   a predicate holds at every node of a tree: *)

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

(* examples  *) 

Definition ex_tree : tree string :=
  (Node (Node Empty 2 "two" Empty) 5 "five" (Node Empty 8 "eight" Empty))%string.

Goal BST ex_tree.
Proof.
  unfold ex_tree. repeat constructor.
Qed.

Example not_BST_ex :  ~ BST (Node ex_tree 0 "zero" Empty)%string.
Proof.
  unfold ex_tree. intro.
  inversion_clear H. inversion_clear H0. lia.
Qed.

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

Module Tests.

(* Some unit tests to check that BSTs behave the way we expect. *)

  Open Scope string_scope.

  Example bst_ex1 :
    insert 8 "eight" (insert 2 "two" (insert 5 "five" empty_tree)) = ex_tree.
  Proof. reflexivity. Qed.

  Example bst_ex2 : lookup "" 2 ex_tree = "two".
  Proof. reflexivity. Qed.

  Example bst_ex3 : lookup "" 3 ex_tree = "".
  Proof. reflexivity. Qed.

  Example bst_ex4 : bound 3 ex_tree = false.
  Proof. reflexivity. Qed.

  Example bst_ex5 : lookupBT 3 ex_tree = None.
  Proof. reflexivity. Qed.

  Example bst_ex6 : lookupBT 5 ex_tree = Some "five".
  Proof. reflexivity. Qed.
  
  Example bst_ex7 :
    BST (insert 8 "eight" (insert 2 "two" (insert 5 "five" empty_tree))).
  Proof. repeat constructor. Qed.
  
End Tests.

(* ======================================================================== *)
(* ==================== Properties of BST operations ====================== *)

(* Prove that the empty tree is a BST. *)

Theorem empty_tree_BST : forall (A : Type),  BST (@empty_tree A).                
Proof.
  constructor.
Qed.

(* Proceed by induction on the evidence that (ForallBT P t). *)

Lemma ForallBT_insert : forall (A : Type) (P : key -> A -> Prop) (t : tree A),
       ForallBT P t -> forall (k : key) (a : A), P k a -> ForallBT P (insert k a t).
Proof.
  intros. induction H. 
  - simpl. constructor. 
    + assumption.
    + constructor.
    + constructor.
  - simpl. destruct (k <?? k0). 
    + constructor; assumption. 
    + destruct (k >?? k0).
      * constructor; assumption.
      * constructor; assumption.
Qed.

(* Now prove the main theorem. Proceed by induction on the evidence that t is a BST. *)

Theorem insert_BST : forall (A : Type) (k : key) (a : A) (t : tree A),
                           BST t -> BST (insert k a t).
Proof.
  intros. induction H.
  - simpl. repeat constructor.
  - simpl. destruct (k <?? x). 
    + constructor; try assumption. apply ForallBT_insert; auto.
    + destruct (k >?? x). 
      * constructor; try assumption. apply ForallBT_insert; auto.
      * cut (k = x). 
        -- intros. rewrite H3. constructor; try assumption.
        -- lia.
Qed.

(* ======================================================================== *)

Theorem lookup_empty : forall (A : Type) (d : A) (k : key),
    lookup d k empty_tree = d.
Proof.
  auto.
Qed.

Theorem lookup_insert_eq : forall (A : Type) (t : tree A) (d : A) (k : key) (a : A),
    lookup d k (insert k a t) = a.
Proof.
  induction t; intros; simpl.
  - destruct (k <?? k); destruct (k >?? k); try lia; auto.    
  - destruct (k0 <?? k); destruct (k0 >?? k); simpl; try lia; auto.
    + destruct (k0 <?? k); destruct (k0 >?? k); try lia; auto.
    + destruct (k0 <?? k); destruct (k0 >?? k); try lia; auto.
    + destruct (k0 <?? k0); destruct (k0 >?? k0); try lia; auto.
Qed.

(* The basic method of this proof is to repeatedly destruct
   the guard of the "if" in sight, followed by use of lia and auto tatics.

    We can automate that, by defining a new tatics that implements the strategy.
 *)

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

Theorem lookup_insert_eq' :
  forall (A : Type) (t : tree A) (d : A) (k : key) (a : A),
    lookup d k (insert k a t) = a.
Proof.
  intros. induction t; dall.
Qed.

Theorem lookup_insert_neq :
  forall (A : Type) (t : tree A) (d : A) (k k' : key) (a : A),
   k <> k' -> lookup d k' (insert k a t) = lookup d k' t.
Proof. 
  intros. induction t; dall.
Qed.

(* ======================================================================== *)
(* ================ Properties of the Inorder Traversal =================== *)

(* We want to show that the result of the inorder traversal of a BST is sorted by key *) 

Fixpoint inorderKeys {A : Type} (t : tree A) : list key :=
  match t with
  | Empty => []
  | Node l k a r => inorderKeys l ++ [k] ++ inorderKeys r
  end.

(* reacall the Sorted predicate over lists of integers *)

Inductive Sorted : list Z -> Prop := 
  | sorted0 : Sorted nil 
  | sorted1 : forall z:Z, Sorted (z :: nil) 
  | sorted2 : forall (z1 z2:Z) (l:list Z), 
        z1 <= z2 -> Sorted (z2 :: l) -> Sorted (z1 :: z2 :: l). 

(* Our goal is to prove the following theorem:

      forall (A : Type) (t : tree A),  BST t -> Sorted (inorderKeys t)
*)

(* The proof of this theorem proceed by induction on the evidence that t is a BST. *)

Theorem sorted_inorderKeys : forall (A : Type) (t : tree A),  BST t -> Sorted (inorderKeys t).
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl.
            (* We need to prove that inserting an intermediate value
               between two lists maintains sortedness. *)
Abort.

(* The following lemma will be very helpful:

 Lemma sorted_app: forall l1 l2 x,
  Sorted l1 -> Sorted l2 ->
  Forall (fun n => n <= x) l1 -> Forall (fun n => n >= x) l2 ->
  Sorted (l1 ++ x :: l2).
*)

(* The predicate Forall is defined in List library *)
Print Forall.
(*
Inductive Forall (A : Type) (P : A -> Prop) : list A -> Prop :=
    Forall_nil : Forall P []
  | Forall_cons : forall (x : A) (l : list A), P x -> Forall P l -> Forall P (x :: l).
 *)

(* This property, proved im List library, will by certainly useful. *)
Check Forall_app.
(*
Forall_app
     : forall (A : Type) (P : A -> Prop) (l1 l2 : list A),
       Forall P (l1 ++ l2) <-> Forall P l1 /\ Forall P l2
*)

(* ======================== Some auxiliary lemmas ======================== *)

(* ======================================================================== *)
(* we will need some lemmata relating the predicates ForallBT and Forall    *)

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

Lemma ForallBT_Forall_le : forall A x t,
    ForallBT (fun (y : key) (_ : A) => y <= x) t -> Forall (fun n : Z => n <= x) (inorderKeys t).
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl. (*apply Forall_app.*) rewrite Forall_app. split.
    + assumption.
    + constructor; assumption.
Qed.

Lemma ForallBT_Forall_ge : forall A x t,
    ForallBT (fun (y : key) (_ : A) => y >= x) t -> Forall (fun n : Z => n >= x) (inorderKeys t).
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl. (*apply Forall_app.*) rewrite Forall_app. split.
    + assumption.
    + constructor; assumption.
Qed.

(* ======================================================================== *)
(* we will need some lemmata about the Sorted predicate                     *)

Lemma sorted_cons_le : forall x y l, x <= y -> Sorted (y::l) -> Sorted (x :: l).
Proof.
  intros. induction l.
  - constructor.
  - constructor.
    + inversion H0. lia.
    + inversion H0. assumption.
Qed.

Lemma sorted_cons : forall x l, Forall (fun n : Z => n >= x) l -> Sorted l -> Sorted (x :: l).
Proof.
  intros. induction H0.
  - constructor.
  - constructor.
    + inversion H. lia.
    + constructor.
  - constructor.
    + inversion H. lia.
    + constructor; auto.
Qed.

Lemma sorted_Forall : forall x l, Sorted (x :: l) -> Forall (fun n : Z => n >= x) l.
Admitted.

(* ======================================================================== *)
(* we will need some lemmata about the Forall predicate                     *)

Lemma Forall_lt_le : forall x l, Forall (fun n : Z => n > x) l -> Forall (fun n : Z => n >= x) l.
Admitted.
   

Lemma Forall_le_le : forall x y l, x >= y -> Forall (fun n : Z => n >= x) l -> Forall (fun n : Z => n >= y) l.
Admitted.




(* ======================================================================== *)
(* we will need some lemmata about the ForallBT predicate                   *)

Lemma ForallBT_lt_le : forall A x t,
    ForallBT (fun (y : key) (_ : A) => y < x) t -> ForallBT (fun (y : key) (_ : A) => y <= x) t.
Admitted.



Lemma ForallBT_gt_ge : forall A x t,
    ForallBT (fun (y : key) (_ : A) => y > x) t -> ForallBT (fun (y : key) (_ : A) => y >= x) t.
Admitted.



(* ============ Completing the proof of theorem sorted_inorderKeys ========= *)

(* ========================================================================== *)
(* Prove the sorted_app lemma by induction on the evidence that l1 is sorted. *)

Lemma sorted_app : forall l1 l2 x,
                      Sorted l1 -> Sorted l2 ->
                      Forall (fun n => n <= x) l1 ->
                      Forall (fun n => n >= x) l2 ->
                      Sorted (l1 ++ x :: l2).
Admitted.

(* ======================================================================== *)
(* Prove that the inorder traversal of a BST is a sorted list.                *)
(* Proceed by induction on the evidence that t is a BST.                    *)

Theorem sorted_inorderKeys : forall (A : Type) (t : tree A),
    BST t -> Sorted (inorderKeys t).
Proof.
  intros. induction H.
  - simpl. constructor.
  - simpl.  Admitted.
