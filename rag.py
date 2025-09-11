import pandas as pd

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import ChatOpenAI

import config

#1. 准备和加载数据
df = pd.read_excel("data/出行信息服务在线客服知识库.xlsx")
#2.出行信息服务在线客服知识库.xlsx
documents = []
for index, row in df.iterrows():
    # 核心：page_content是用于检索的文本，metadata里存放真正的答案
    question = row['知识标题']
    similar_questions = row['相似问法'] if pd.notna(row['相似问法']) else row['知识标题']

    combined_questions = f"{question}\n{similar_questions}"
    answer = row['答案（默认)【富文本】']
    if not combined_questions:
        print(f"Skipping empty row at Excel index {index + 2}.")
        continue
    doc = Document(
        page_content=combined_questions,
        metadata={
            'answer': answer,
            'source_question': question  # 也可以把原始问题存起来，方便溯源
        }
    )
    documents.append(doc)
print("--- 创建的文档示例 ---")
print(documents[0])
print("-" * 20)
#3. 创建向量数据库
embeddings = DashScopeEmbeddings(
    model="text-embedding-v2"
)
text = "This is a test document."

vector_store = FAISS.from_documents(documents, embeddings)
print("--- 创建向量数据库成功 ---")
retriever = vector_store.as_retriever()

# --- 4. 运行RAG链 ---
template = """
根据以下背景知识，简洁明了地回答问题。

背景知识:
{context}

问题: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

# 从检索到的文档中提取元数据里的answer'
def format_docs(docs):
    # 从每个文档的metadata中提取'answer'字段，并用换行符连接
    return "\n\n".join(doc.metadata['answer'] for doc in docs)
llm = ChatOpenAI(
    model=config.LLM_MODEL_NAME,
    api_key=config.OPENAI_API_KEY,
    base_url=config.OPENAI_API_BASE,
    temperature=0.7,
)
rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
)





