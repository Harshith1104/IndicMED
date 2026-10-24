from __future__ import annotations

import streamlit as st

from src.pipeline import IndicMedPipeline

DISCLAIMER = ("IndicMed provides general health information retrieved from medical information sources "
              "and is not a substitute for professional medical advice, diagnosis, or treatment.")

st.set_page_config(page_title="IndicMed", page_icon="🩺")
st.title("IndicMed")
st.caption("Multilingual Medical Information Retrieval")
st.info(DISCLAIMER)


@st.cache_resource
def load_pipeline() -> IndicMedPipeline:
    return IndicMedPipeline()


labels = {"Auto detect": "auto", "English": "en", "हिन्दी": "hi", "తెలుగు": "te", "தமிழ்": "ta"}
language_label = st.selectbox("Language", list(labels))
selected_language = labels[language_label]
query = st.text_area("Ask a health-information question")
with st.expander("Advanced settings"):
    method = st.selectbox("Retrieval method", ["tfidf", "bm25", "semantic"], index=2)
    strategy_label = st.selectbox(
        "Multilingual strategy",
        ["Translate to English then retrieve", "Direct multilingual retrieval"],
        help="Translation performed better overall in the validated multilingual experiment.",
    )
    top_k = st.slider("Number of results", 1, 5, 3)
strategy = "translate" if strategy_label.startswith("Translate") else "direct"

if st.button("Ask IndicMed", type="primary"):
    if not query.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Searching trusted medical FAQs..."):
                response = load_pipeline().ask(
                    query, selected_language, method, top_k, multilingual_strategy=strategy
                )
            st.subheader(response["category"] or "Retrieved answer")
            st.write(response["translated_answer"])
            if response.get("translation_warning"):
                st.warning(response["translation_warning"])
            if response["source_url"]:
                st.markdown(f"**Source:** [{response['source']}]({response['source_url']})")
            else:
                st.write(f"**Source:** {response['source']}")
            st.write(f"**Similarity:** {response['similarity_score']:.3f}")
            if response["related_questions"]:
                st.write("**Related questions**")
                for item in response["related_questions"]:
                    st.write(f"- {item}")
            with st.expander("Technical details"):
                st.write(f"**Original query:** {response['query']}")
                st.write(f"**English query:** {response['english_query']}")
                st.write(f"**Retrieval strategy:** {response['retrieval_strategy']}")
                st.write(f"**Document ID:** {response['document_id']}")
                if response["detected_language"] != "en":
                    st.write("**Grounded English answer:**")
                    st.write(response["answer"])
        except Exception as error:
            st.error(str(error))
