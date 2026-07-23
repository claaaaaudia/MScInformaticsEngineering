# Ricart–Agrawala Algorithm in Mutual Exclusion in Distributed System

Ricart–Agrawala algorithm is an algorithm for mutual exclusion in a distributed system proposed by Glenn Ricart and Ashok Agrawala. This algorithm is an extension and optimization of Lamport's Distributed Mutual Exclusion Algorithm. Like Lamport's Algorithm, it also follows permission-based approach to ensure mutual exclusion. In this algorithm:

- Two type of messages ( REQUEST and REPLY) are used and communication channels are assumed to follow FIFO order.
- A site send a REQUEST message to all other site to get their permission to enter the critical section.
- A site send a REPLY message to another site to give its permission to enter the critical section.
- A timestamp is given to each critical section request using Lamport's logical clock.
- Timestamp is used to determine priority of critical section requests. Smaller timestamp gets high priority over larger timestamp. The execution of critical section request is always in the order of their timestamp.

## Algorithm:

- To enter Critical section:
    - When a site Si wants to enter the critical section, it send a timestamped REQUEST message to all other sites.
    - When a site Sj receives a REQUEST message from site Si, It sends a REPLY message to site Si if and only if
        - Site Sj is neither requesting nor currently executing the critical section.
        -In case Site Sj is requesting, the timestamp of Site Si's request is smaller than its own request.
- To execute the critical section:
    - Site Si enters the critical section if it has received the REPLY message from all other sites.
- To release the critical section:
    - Upon exiting site Si sends REPLY message to all the deferred requests.



## Implementation:

**Local variables:**

- #replies (initially 0)
– State $\in$ {Requesting, CS, NCS} (initially NCS)
– Q pending requests queue (initially empty)
– Last_Req (initially MAX_INT)
– Num (initially 0)

**Assumptions:**

- processes don’t fail
- messages are never lost
- finite channel latencies (value is unknown)

---

**repeat**

1. State = Requesting
2. Num = Num + 1; Last_Req = num
3. $ \forall i = 1...N $, send REQUEST(Last_Req) to $p_i$
4. Wait until #replies == N - 1
5. State = CS
6. CS
7. $ \forall r \in Q$, send REPLY to r

    $Q = \empty $; State = NCS; #replies = 0;

    Last_Req = MAX_INT

Note: line 2 is executed atomically



**Upon receipt of REQUEST(t) from $p_j$**

8. Num = max(t, Num)
9. If State == CS or (State == Requesting and {Last_Req,i} < {t,j})
10. Then insert {t, j} into Q
11. Else send REPLY to $p_j$



**Upon receipt of REPLY from $p_j$**

12. #replies = #replies + 1

---