import json
import faiss
import numpy as np
import os
from typing import List, Dict, Optional
from api.api_client import APIClient

class KnowledgeBase:

    def __init__(self, api_client: APIClient, law_library_path: str):

        self.api_client = api_client
        self.law_library_path = law_library_path
        self.laws = []
        self.index = None

        self.embeddings_cache_path = os.path.join(os.path.dirname(__file__), "law_embeddings.npy")
        self.index_cache_path = os.path.join(os.path.dirname(__file__), "law_index.faiss")

        self._load_laws()

    def _load_laws(self):

        print("正在加载法条库...")
        with open(self.law_library_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.laws.append(json.loads(line))
        print(f"法条库加载完成，共{len(self.laws)}条法条")

    def build_index(self):

        if (os.path.exists(self.embeddings_cache_path) and
            os.path.exists(self.index_cache_path)):
            print("发现缓存的索引，正在加载...")
            self._load_cached_index()
            return

        print("正在构建法条向量索引...")
        embeddings = []
        for i, law in enumerate(self.laws):
            if i % 100 == 0:
                print(f"已处理 {i}/{len(self.laws)} 条法条...")
            embedding = self.api_client.get_embedding(law['content'])
            embeddings.append(embedding)

        embeddings_array = np.array(embeddings).astype('float32')
        dimension = embeddings_array.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        faiss.normalize_L2(embeddings_array)
        self.index.add(embeddings_array)
        print("向量索引构建完成")

        print("正在保存索引缓存...")
        np.save(self.embeddings_cache_path, embeddings_array)
        faiss.write_index(self.index, self.index_cache_path)
        print("索引缓存已保存")

    def _load_cached_index(self):

        embeddings_array = np.load(self.embeddings_cache_path)
        dimension = embeddings_array.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings_array)
        print(f"缓存索引加载完成，共 {self.index.ntotal} 条法条")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:

        if self.index is None:
            self.build_index()

        query_embedding = self.api_client.get_embedding(query)
        query_vector = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_vector)

        distances, indices = self.index.search(query_vector, top_k)

        results = []
        for idx in indices[0]:
            if idx < len(self.laws):
                law = self.laws[idx]
                results.append({
                    'name': law['name'],
                    'content': law['content']
                })

        return results

    def format_laws(self, laws: List[Dict[str, str]]) -> str:

        formatted = []
        for law in laws:
            formatted.append(f"{law['name']}: {law['content']}")
        return "\n\n".join(formatted)
