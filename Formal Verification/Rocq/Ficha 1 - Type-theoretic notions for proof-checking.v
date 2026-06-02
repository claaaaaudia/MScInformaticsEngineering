(* ============================== Ficha 1 ============================== *)

Section PropositionalLogic.

(* The main tools are destruct, split, left, right, and exact. The pattern is:

   Conjunction (/\): split to break goals, destruct to break hypotheses
   
   Disjunction (\/): left/right to choose a branch in goals, destruct to case-split hypotheses
   
   Biconditional (<->): split into two directions, then handle each
*)

Variables A B C : Prop.

Lemma a1 : (A \/ B) \/ C -> A \/ (B \/ C).
Proof.
  intros H.
  destruct H as [[Ha|Hb]|Hc].
  - left. exact Ha.
  - right. left. exact Hb.
  - right. right. exact Hc.
Qed.

Lemma a2 : (B -> C) -> A \/ B -> A \/ C.
Proof.
  intros H0 H1.
  destruct H1 as [Ha|Hb].
  - left. exact Ha.
  - right. apply H0. exact Hb.
Qed.

Lemma a3 : (A /\ B) /\ C -> A /\ (B /\ C).
Proof.
  intros H.
  destruct H as [[Ha Hb] Hc].
  split. 
  - exact Ha.
  - split. 
    + exact Hb.
    + exact Hc. 
Qed.

Lemma a4 : A \/ (B /\ C) -> (A \/ B) /\ (A \/ C).
Proof.
  intro H.
  destruct H as [Ha | [Hb Hc]].
  - split. 
    + left. exact Ha.
    + left. exact Ha.
  - split.
    + right. exact Hb.
    + right. exact Hc.
Qed.

Lemma a5 : (A /\ B) \/ (A /\ C) <-> A /\ (B \/ C).
Proof.
  split.
  - (* -> direction *)
    intros H.
    destruct H as [[HA HB] | [HA HC]].
    + split.
      * exact HA.
      * left. exact HB.
    + split.
      * exact HA.
      * right. exact HC.

  - (* <- direction *)
    intros H.
    destruct H as [HA [HB | HC]].
    + left. split; assumption.
    + right. split; assumption.
Qed.

Lemma a6 : (A \/ B) /\ (A \/ C) <-> A \/ (B /\ C).
Proof.
  split.
  - intros [[HA | HB] [HA' | HC]].
    + left. exact HA.
    + left. exact HA.
    + left. exact HA'.
    + right. split. exact HB. exact HC.
  - intros [HA | [HB HC]].
    + split; left; exact HA.
    + split; right; assumption.
Qed.

End PropositionalLogic.

(* ===================================================================== *)

Section FirstOrderLogic.

(* Same tools as above, plus exists and apply. The pattern is:

   Existential (exists): provide a witness with exists x in goals, 
                                      destruct to extract witness from hypotheses

   Universal (forall): intros to bring variables into context, 
                                      apply to use universally quantified hypotheses
*)

Variable X : Type. 
Variable Y : Type.
Variable P Q R : X -> Prop.
Variable P2 : X -> Y -> Prop.
Variable Q2 : Y -> Prop.

Lemma b1 : (exists x : X, P x /\ Q x) -> (exists x : X, P x) /\ (exists x : X, Q x).
Proof.
  intros H.
  destruct H as [x [HP HQ]].
  split.
  - exists x. exact HP.
  - exists x. exact HQ.
Qed.

Lemma b2 : (exists x : X, forall y : Y, P2 x y) -> forall y : Y, exists x : X, P2 x y.
Proof.
  intros H y.
  destruct H as [x HP].
  exists x.
  apply HP.
Qed.

Lemma b3 : (exists x : X, P x) -> (forall x : X, forall y : Y, P x -> Q2 y) -> forall y : Y, Q2 y.
Proof.
  intros.
  destruct H as [x HP].
  exact (H0 x y HP).
Qed.

Lemma b4 : (forall x : X, Q x -> R x) -> (exists x : X, P x /\ Q x) -> exists x : X, P x /\ R x.
Proof.
  intros Himp H.
  destruct H as [x [HP HQ]].
  exists x.
  split.
  - exact HP.
  - apply Himp. exact HQ.
Qed.

Lemma b5 : (forall x : X, P x -> Q x) -> (exists x : X, P x) -> (exists z : X, Q z).
Proof.
  intros.
  destruct H0 as [x HP].
  exists x.
  exact (H x HP). 
Qed.

Lemma b6 : ((exists x : X, P x) \/ (exists x : X, Q x)) <-> (exists x : X, P x \/ Q x).
Proof.
  split.
  - intros. destruct H as [HP|HQ].
    + destruct HP as [x HP']. exists x. left. exact HP'.
    + destruct HQ as [x HQ']. exists x. right. exact HQ'.
  - intros. destruct H as [x HPQ]. destruct HPQ as [HP''|HQ''].
    + left. exists x. exact HP''.
    + right. exists x. exact HQ''.
Qed.

End FirstOrderLogic.

(* ===================================================================== *)

(* Requires the excluded middle axiom (PEM), not provable in intuitionistic logic.
   The pattern is always:

   destruct (PEM X) to case-split on whether X is true or false

   Positive case: use the hypothesis directly

   Negative case: use exfalso to derive a contradiction
*)

Section ClassicalLogic.

Variables A B : Prop.

Axiom PEM : forall P : Prop, P \/ ~ P. (* Assuming the principle of the excluded middle *)

Lemma pierce : ((A -> B) -> A) -> A.
Proof.
  intros H.
  destruct (PEM A) as [HA | HNA].
  - (* Case A true *)
    exact HA.
  - (* Case A false*)
    apply H.
    intros HA'.
    exfalso. (* _|_ -> P *)
    apply HNA.
    exact HA'.
Qed.

Lemma notnotA : ~~A -> A.
Proof.
  intros H.
  destruct (PEM A) as [HA | HNA].
  - exact HA.
  - exfalso. apply H. exact HNA.
Qed.

Variable U : Type.
Variable P : U -> Prop.

Lemma notforall_exists : (~ forall x, P x) -> exists x, ~ P x.
Proof.
  intros H.
  destruct (PEM (exists x, ~ P x)) as [HE | HNE].
  - exact HE.
  - exfalso. apply H.
    intros x.
    destruct (PEM (P x)) as [HP | HNP].
    + exact HP.
    + exfalso. apply HNE.
      exists x. exact HNP.
Qed.

End ClassicalLogic.
