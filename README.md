# Humanity Compatible: Kantian Alignment for Large Language Models

## Introduction
In *Models of Rational Agency in Human-Centered AI: The Realist and Constructivist Alternatives*, Professors Jacob Sparks and Ava Wright propose that, to best align with human interests, AI should adopt a non-economic model of human rational agency [1].  
Humanity Compatible works to realize this framework by fine-tuning a large language model (LLM) to interpret human prompts through an implicit Kantian framework, with the goal of creating a helpful model that enables human autonomy.

---

## Methods

### Overview
Our alignment technique adapts Bai et al. (2022)’s Constitutional AI (CAI) method [2], a self-improvement pipeline in which the model refines its own responses for alignment.  
Due to time and resource constraints, we made several modifications:  
- All fine-tuning was performed with QLoRA (4-bit).  
- We replaced the final PPO RL stage with a lightweight DPO run.  
- We used Llama-3.3-70B-Instruct as our base model for its accessibility and strong performance.  
- ChatGPT-5 was used for preference judging.  
- All compute-intensive tasks ran on an NVIDIA H200 SXM instance via RunPod.

---

### Supervised Fine-Tuning (SFT)
We began by generating 10,000 responses from the base model, primarily to red-team prompts, with a smaller portion of benign examples for balance.  
The base model then critiqued and rewrote its own responses according to a set of hand-crafted Kantian principles.  
These improved responses were used to fine-tune the base model, producing the SFT model.

---

### Preference Data (PD) Generation
To generate preference data, we produced paired responses at different temperatures (t = 0.7, 1.0) from our SFT model using the same red-team prompts.  
We then used GPT-5 (chosen for its advanced reasoning capability) to label and refine preferred responses, judging each according to a concise list of Kantian ethical principles.

---

### Direct Preference Optimization (DPO)
In the final stage, we trained the base + SFT-adapter configuration with DPO, using the curated preference data to further shift model behavior toward our Kantian reasoning framework.

---

## Results

### Constitutional Alignment
We successfully replicated the CAI pipeline to produce a harmless yet helpful model, guided by Kantian principles rather than the ad hoc constitution of the original work [1, 2].  
Our model exhibits distinctly Kantian reasoning, identifying maxims of action and testing them against moral principles.

---

### Key Case Evaluation
We qualitatively evaluated the tuned model on 16 moral and autonomy-related prompts.  
Professor Wright found that the tuned model produced superior analysis in six cases—two slight, two moderate, and two strong improvements—including three cases where the tuned model provided principled, safe responses where the base model refused to respond.  
These outcomes highlight the value of Kantian reasoning for ethical deliberation in AI systems.

---

### MT-Bench Evaluation
We also evaluated both models using MT-Bench, which scores LLMs across eight reasoning and interaction categories using GPT-4 as judge [3].  

| Model | Average Score |
|--------|----------------|
| BASE | 8.24 |
| SFT_DPO | 8.08 |

The tuned model performed slightly below the base overall, with gains in STEM, humanities, and roleplay, but losses in reasoning, math, coding, and extraction.  
We interpret this as evidence that current automated judging benchmarks fail to capture philosophically grounded reasoning.  

Future work should develop evaluation frameworks that assess ethical reasoning and autonomy, and explore hybrid alignment techniques incorporating explicit moral reasoning structures.

---

## References
1. J. Sparks, A. Wright. *Models of Human Rationality in Human-Centered AI: The Realist and Constructivist Alternatives.* [PhilArchive](https://philarchive.org/rec/SPAMOR)  
2. Y. Bai et al. *Constitutional AI: Harmlessness from AI Feedback.* arXiv:2212.08073 (2022). [arXiv Link](https://arxiv.org/abs/2212.08073)  
3. L. Zheng et al. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* arXiv:2306.05685 (2023).

---

## Acknowledgements
This research was funded by Cal Poly’s Noyce School of Applied Computing.
