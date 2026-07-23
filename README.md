# 🎓 Master’s in Informatics Engineering — University of Minho

This repository is a curated collection of projects and lab assignments developed throughout my Master’s degree in Informatics Engineering at the University of Minho.

Each folder contains the corresponding source code and reports for specific courses. Below is an overview of the projects, along with their main goals and the skills acquired.

---

## 📊 Data and Machine Learning

A project focused on **predicting road traffic conditions in Porto** using Machine Learning techniques and real-world data.

Traffic is modeled as a **dynamic system** influenced by factors such as:
- Time
- Weather

The main objective is to classify congestion levels based on the variable *average speed diff*, helping improve urban mobility and congestion management.

**Workflow Highlights:**
- Exploratory Data Analysis (EDA)
- Data preprocessing (cleaning, missing values, feature engineering)
- Model training and optimization
- Techniques: Bagging, Boosting, Stacking, Ensemble methods
- Hyperparameter tuning (Grid Search, Random Search)
- Evaluation using accuracy and benchmarking (e.g., Kaggle)

🎯 **Skills acquired:**  
`Data Analysis` · `Predictive Modeling` · `Model Optimization` · `Comparative Analysis`

---

## 🌐 Network Services Engineering

Development of an **Over-the-Top (OTT) multimedia streaming service**.

The system is designed to deliver **real-time multimedia content efficiently** using an application-level overlay network between servers and clients.

**Technical Highlights:**
- Implemented in Python  
- Hybrid communication model:
  - TCP → reliable control messages  
  - UDP → fast multimedia streaming  

This approach ensures a balance between **reliability and performance**.

🎯 **Skills acquired:**  
`Network Design` · `Distributed Systems` · `Communication Protocols`

---

## 📷 Software Requirements and Architectures

**PictuRAS** is a web-based image editing platform combining traditional tools with AI-powered features.

Built using a **microservices architecture**, it offers:
- Image editing tools  
- Visual effects  
- AI-based enhancements  

This project builds upon a pre-existing system developed by previous students.

**Project Phases:**
1. Analysis of the existing solution  
2. Expansion of requirements  
3. Implementation of new features  

🎯 **Skills acquired:**  
`Requirements Engineering` · `Software Design` · `Frontend & Backend Development` · `APIs` · `Microservices`

---

## 🚗 New Network Paradigms

Development and evaluation of a **cooperative traffic management system for roadwork zones** using **Vehicle-to-Everything (V2X) communications**.

The project leverages **SUMO** and **Eclipse MOSAIC** to simulate intelligent transportation scenarios where roadworks reduce road capacity and create congestion. To mitigate these effects, a **Road Side Unit (RSU)** was implemented to coordinate traffic through V2I and V2V communications.

**Technical Highlights:**

* Intelligent RSU for traffic monitoring and coordination
* Dynamic speed recommendation system based on:

  * Traffic density
  * Average vehicle speed
  * Queue growth
* Multi-hop information dissemination between vehicles
* Adaptive congestion management policies
* Simulation and evaluation using SUMO and Eclipse MOSAIC

The solution was assessed using metrics such as travel time, bottleneck throughput, and congestion queue evolution, comparing results against a baseline scenario without intelligent coordination.

🎯 **Skills acquired:**
`V2X Communications` · `Intelligent Transportation Systems` · `Network Simulation` · `Traffic Engineering` · `Performance Evaluation`

---

## 💻 Software Defined Networks

Design and implementation of a **dynamic Network Slicing architecture** over a programmable **Software Defined Networking (SDN)** infrastructure using **P4**.

The system consists of a network topology with multiple P4 switches and hosts, providing traffic isolation, bandwidth control, security mechanisms, and automated fault recovery. The architecture combines programmable data planes, telemetry, and containerized network functions to ensure service quality and network resilience.

**Technical Highlights:**

* Network Slicing implementation on programmable P4 switches
* Slice classification and traffic isolation through pipeline metadata
* Bandwidth control using programmable meters
* Stateful firewall based on Bloom Filters
* Dynamic Traffic Shaping using Linux containerized Network Functions (cNFs)
* gRPC-based telemetry for autonomous resource management
* Self-Healing mechanism capable of detecting and recovering from failures in under 5 seconds

The solution was validated through performance and fault-tolerance experiments, demonstrating effective slice isolation, SLA compliance, and resilience under induced failures.

🎯 **Skills acquired:**
`Software Defined Networking (SDN)` · `P4 Programming` · `Network Slicing` · `Network Security` · `Traffic Engineering` · `Network Automation`

---

## 🚀 Cyber-Physical Programming

A course focused on the **modeling, analysis, and verification of cyber-physical systems**, combining formal methods, concurrency, and system correctness techniques.

### ✈️ Project 1 — The Curious Case of an Airport

Development and formal verification of an **airport traffic management system** using **Uppaal**.

The project models the interaction between planes, runways, and a controller responsible for coordinating takeoff and landing requests. The system was analyzed through reachability, safety, and liveness properties to ensure correct behavior under concurrent access to shared resources.

**Technical Highlights:**

* Modeling with Uppaal timed automata
* Verification of safety and liveness properties
* Runway allocation and controller design
* Deadlock detection and prevention
* Analysis of starvation and fairness issues

🎯 **Skills acquired:**
`Formal Methods` · `Model Checking` · `Uppaal` · `Timed Automata` · `Concurrent Systems` · `System Verification`

### 🌉 Project 2 — The Rope Bridge Problem

Modeling and analysis of a classic **resource-constrained synchronization problem** using **functional programming and monads**.

The challenge consists of finding the optimal strategy for four adventurers to cross a bridge with a single flashlight while minimizing total crossing time. The project explores deterministic, non-deterministic, and probabilistic system behaviors through monadic abstractions in Haskell.

**Technical Highlights:**

* Functional modeling in Haskell
* Use of Duration and Non-Deterministic Monads
* Verification and probabilistic modeling of optimal crossing strategies
* Computation of state distributions and execution outcomes

The project demonstrates how monads can be used to model complex cyber-physical behaviors, reason about uncertainty, and analyze system outcomes through both deterministic and probabilistic perspectives.

🎯 **Skills acquired:**
`Functional Programming` · `Haskell` · `Monads` · `State Space Exploration` · `Probabilistic Modeling` · `System Analysis`


---

✨ *Feel free to explore each folder for code, reports, and implementation details.*