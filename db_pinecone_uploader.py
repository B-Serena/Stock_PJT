# db uploading with klue/roberta-base as a sentence embedding model

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import json
import os
from dotenv import load_dotenv
import re

# .env 파일에서 환경 변수 로드
load_dotenv()

def load_crawled_data(file_path='crawled_data.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def preprocess_text(text):
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_key(key):
    return re.sub(r'[^a-z0-9-]', '', key.lower().replace(' ', '-'))

def upload_to_pinecone(data):
    # 환경 변수에서 Pinecone 설정 가져오기
    api_key = os.getenv('PINECONE_API_KEY')
    cloud = os.getenv('PINECONE_CLOUD', 'aws')
    region = os.getenv('PINECONE_REGION')

    if not api_key or not region:
        raise ValueError("Pinecone API 키 또는 리전이 설정되지 않았습니다. 환경 변수를 확인해주세요.")

    # Pinecone 인스턴스 생성
    pc = Pinecone(api_key=api_key)

    # 인덱스 이름 설정
    index_name = "kurlyproducts-klue-roberta-base"

    # 인덱스가 존재하지 않으면 생성
    try:
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=768,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud=cloud,
                    region=region
                )
            )
        print(f"인덱스 '{index_name}' 생성 또는 연결 완료")

        # 인덱스 연결
        index = pc.Index(index_name)
        print("index connected")

        # 문장 임베딩 모델 로드 (한국어에 적합한 모델 사용)
        model = SentenceTransformer('klue/roberta-base')
        print("model embedded")

        print("model uploading start")
        # 데이터를 Pinecone에 업로드
        batch_size = 100
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            ids = [clean_key(str(item["id"])) for item in batch]
            texts = [preprocess_text(item.get('all_text', '')) for item in batch]
            embeddings = model.encode(texts).tolist()
            metadata = [{
                clean_key(k): v for k, v in {
                    "category": item.get("category", ""),
                    "url": item.get("url", "")
                }.items() if v
            } for item in batch]
            to_upsert = list(zip(ids, embeddings, metadata))
            index.upsert(vectors=to_upsert)
            print(f"{i+len(batch)}개의 상품 정보를 Pinecone에 업로드했습니다.")

        print(f"총 {len(data)}개의 상품 정보를 Pinecone에 업로드 완료했습니다.")

    except Exception as e:
        print(f"Pinecone 작업 중 오류 발생: {e}")
        if hasattr(e, 'response'):
            print(f"응답 상태 코드: {e.response.status_code}")
            print(f"응답 내용: {e.response.text}")

if __name__ == "__main__":
    try:
        # 크롤링한 데이터 불러오기
        crawled_data = load_crawled_data()
        # Pinecone에 데이터 업로드
        upload_to_pinecone(crawled_data)
    except Exception as e:
        print(f"전체 프로세스 중 오류 발생: {e}")