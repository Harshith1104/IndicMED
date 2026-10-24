If I were interviewing you for an **AI Engineer role**, I would use IndicMed to assess your ownership, technical understanding, and ability to evaluate an AI system.

**Project introduction and ownership**

1. Walk me through IndicMed in two minutes. What problem does it solve?
2. What was your individual contribution to the project?
3. Why did you choose a multilingual medical FAQ application?
4. What was the most difficult technical challenge, and how did you resolve it?
5. What would you improve if you had another month?

**Architecture and design**

6. Explain the complete pipeline from a Telugu question to the final Telugu answer.
7. Why did you maintain one English knowledge base instead of translating the entire dataset?
8. Why did you choose retrieval-based answers instead of generating answers with an LLM?
9. Would you describe IndicMed as RAG? How does it differ from a typical generative RAG application?
10. What happens when query translation or answer translation fails?

**Embeddings and retrieval**

11. What is an embedding, and what does a 384-dimensional vector represent?
12. Why did you choose `paraphrase-multilingual-MiniLM-L12-v2`?
13. Why did you embed the FAQ answers instead of the questions?
14. How does cosine similarity work, and why do you normalize vectors?
15. How do TF-IDF, BM25, and semantic retrieval differ?
16. Why did semantic retrieval outperform the keyword-based methods in your experiment?
17. Why did you use NumPy instead of FAISS or a vector database?
18. What happens when an answer exceeds the embedding model’s input limit?
19. How would you introduce hybrid retrieval and reranking?
20. How would retrieval change if your dataset grew from 16,359 documents to one million?

**Multilingual NLP and models**

21. What are the roles of MiniLM and IndicTrans2 in your system?
22. Why do you need two translation checkpoints?
23. Why did translating queries into English outperform direct multilingual retrieval?
24. What could explain the weak direct retrieval results for Telugu and Tamil?
25. How does automatic language detection work? When might it fail?
26. How would you support Romanized Telugu or code-mixed questions?
27. Did you train or fine-tune any models? What would justify fine-tuning?
28. How could translation errors affect retrieval and the final answer?

**Evaluation and reliability**

29. Explain Recall@1, Recall@5, and Mean Reciprocal Rank.
30. Your resume says **74.1% Recall@5**. What exactly does that mean, and how was it measured?
31. How did you avoid matching benchmark questions against identical indexed questions?
32. Are your benchmark questions independent of the source dataset? How does that affect your conclusions?
33. Can a retrieved answer be relevant even when the expected document ID does not match?
34. How would you evaluate translation quality and medical meaning preservation?
35. Does a high similarity score guarantee a correct answer?
36. Your system always selects the first result. How would you handle unrelated questions or low-confidence matches?
37. What does your “answer simplification” component actually do?
38. What do your automated tests verify, and what requires real-model testing?

**Deployment and engineering**

39. How do lazy loading and model caching improve the application?
40. How would you measure and reduce end-to-end response latency?
41. How would you expose this pipeline through an API?
42. How would you handle concurrent users and limited GPU memory?
43. How would you update the dataset and keep the embedding index consistent?
44. What would you monitor after deployment?
45. What changes would be necessary before releasing this as a public medical information application?

**Behavioral and HR questions**

46. Tell me about a result that challenged your original assumptions.
47. Describe a disagreement within your team and how you handled it.
48. How did you divide responsibilities and verify each other’s work?
49. How would you explain this project to a nontechnical stakeholder?
50. Why does your experience with IndicMed make you a good fit for an AI Engineer role?

For each technical answer, follow this structure: **what you implemented → why you chose it → evidence from your results → limitations and next steps**. Be precise about your contribution and distinguish implemented features from proposed improvements.

Let’s start the mock interview:

**“Tell me about yourself and walk me through IndicMed in two minutes, highlighting your personal contribution.”**

Here are interview-ready answers to the first 10 questions. For questions about your contribution and challenges, adjust the wording to reflect what you personally did.

**1. Walk me through IndicMed in two minutes. What problem does it solve?**

“IndicMed is a multilingual medical FAQ retrieval application that supports English, Hindi, Telugu, and Tamil. It helps users access English medical information by asking questions in their own language.

The system uses an English knowledge base containing 16,359 MedQuAD FAQ documents. By default, an Indic-language question is translated into English using IndicTrans2. A multilingual MiniLM model then converts the query into a 384-dimensional embedding, and NumPy cosine similarity identifies the most relevant answer documents.

The application selects the highest-ranked answer, conservatively shortens it, and translates it into the user’s language. A Streamlit interface displays the answer, source, retrieval score, and related questions.

We also compared TF-IDF, BM25, and semantic retrieval. Semantic retrieval achieved 74.1% Recall@5 on 1,000 English benchmark questions. The main design choice was to return existing sourced answers rather than generate new medical advice.”

**2. What was your individual contribution to the project?**

Use this template and replace the brackets honestly:

“My primary responsibility was **[your actual modules or tasks]**. I implemented **[specific functionality]**, integrated it with **[other components]**, and validated it through **[tests or evaluation you performed]**.

For example, **[describe one concrete change you personally made and its result]**. I also collaborated with my teammates on **[shared responsibility]**.

I can explain the complete architecture, while my direct implementation ownership was mainly **[your area]**.”

Avoid claiming that you built the entire pipeline if responsibilities were shared.

**3. Why did you choose a multilingual medical FAQ application?**

“We chose this problem because language can make medical information difficult to access. Many useful resources are available in English, while users may be more comfortable asking questions in Telugu, Hindi, or Tamil.

The project also gave us a practical way to study multilingual NLP: language detection, machine translation, embeddings, and information retrieval within one application.

We kept the scope focused on general medical information from an existing dataset, with source links so users could inspect where an answer came from.”

**4. What was the most difficult technical challenge, and how did you resolve it?**

If this reflects your experience, use:

“One major challenge was retrieving English medical answers from Indic-language questions. We initially evaluated direct multilingual retrieval, where we embedded the original question and searched the English answer vectors.

Our evaluation showed that this performed poorly for Telugu and Tamil. We therefore compared it with a translate-first approach using IndicTrans2.

For Telugu, Recall@1 increased from 1.5% with direct retrieval to 38.0% with translation. Based on those results, we made translate-first retrieval the default and retained direct retrieval as an alternative.

The lesson was that a model’s multilingual capability needs to be evaluated for the actual languages and domain.”

**5. What would you improve if you had another month?**

“My first priority would be handling weak or irrelevant matches. The current system selects the top-ranked result, so I would evaluate a relevance threshold and an abstention response.

Next, I would explore hybrid retrieval combining BM25 and semantic search, followed by reranking. I would compare those changes against the existing benchmark before adopting them.

I would also investigate splitting long answers into passages, support Romanized and code-mixed input, and expand evaluation with independently written user questions and human review of translated answers.”

**6. Explain the complete pipeline from a Telugu question to the final Telugu answer.**

“When a user enters a Telugu question, the system first cleans the text and applies Unicode normalization. It uses the selected language or detects Telugu through its Unicode script.

In the default strategy, IndicTrans2 translates the question into English. The MiniLM embedding model converts that English query into a 384-dimensional vector.

The system normalizes the query vector and compares it with the stored English answer vectors using cosine similarity. It ranks the results and retrieves the top three by default.

It selects the first answer and shortens it to the configured character limit, preferably at a sentence boundary. The English-to-Indic IndicTrans2 model then translates that answer into Telugu.

Finally, Streamlit displays the Telugu answer, source link, retrieval score, and related questions. The shortened English answer is available in the technical details.”

**7. Why did you maintain one English knowledge base instead of translating the entire dataset?**

“We kept one English knowledge base to reduce preprocessing cost, storage, and maintenance.

Translating all 16,359 answers into multiple languages would create additional versions that would need to stay synchronized. It could also introduce translation errors into the stored knowledge base.

With our design, the original English answer remains the reference. We translate the user’s question before retrieval and translate only the selected answer for presentation.

The trade-off is additional translation latency during a request, but it keeps the corpus simpler to maintain and inspect.”

**8. Why did you choose retrieval-based answers instead of generating answers with an LLM?**

“We wanted answers to remain directly traceable to the medical dataset. Retrieving an existing answer gives us a clear source and avoids adding a generative answer model that could introduce unsupported information.

It also makes evaluation more straightforward because we can measure whether the expected document appears in the retrieved results.

However, retrieval does not guarantee medical correctness. The system can select an irrelevant document, the source may be outdated, and translation can alter meaning. That is why the application presents sources and is scoped to general health information.”

**9. Would you describe IndicMed as RAG? How does it differ from a typical generative RAG application?**

“I would describe it more precisely as a retrieval-grounded multilingual FAQ system.

In a typical generative RAG application, retrieved passages are placed into an LLM prompt, and the LLM composes an answer using that context.

IndicMed retrieves an existing FAQ answer and returns it after rule-based shortening and optional translation. It does not use an LLM to synthesize a medical answer from retrieved passages.

It shares the retrieval component of RAG, but its answer stage uses selection and translation rather than generative synthesis.”

**10. What happens when query translation or answer translation fails?**

“The behavior depends on which stage fails.

If query translation is unavailable in translate-first mode, the pipeline raises an error and the UI displays it. The user can switch to direct multilingual semantic retrieval, which searches using the original query. That switch is manual.

If answer translation is unavailable, the pipeline returns the shortened English answer with a warning, so the retrieved information remains accessible.

English queries and answers bypass translation entirely. The translation failures handled this way are those reported through the project’s `TranslationUnavailableError` exception.”
