import os
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# 1. NASTAVENIA (uprav podľa tvojho projektu)
PROJECT_DIR = "C:/tvoj_projekt"  # Cesta k tvojmu projektu
MODEL_NAME = "Qwen/Qwen3-Embedding-8B"  # Model z Hugging Face
SIMILARITY_THRESHOLD = 0.85  # 0.0-1.0 (0.85 = silná shoda)

# 2. NAČÍTANIE MODEL (4-bit kvantizácia pre 64GB RAM)
model = SentenceTransformer(
    MODEL_NAME,
    model_kwargs={"device": "cpu"},  # 3060 + 64GB RAM = CPU je dostatočný
    trust_remote_code=True
)

# 3. GENEROVANIE EMBEDDINGOV pre všetky súbory
files = []
embeddings = []
for root, _, filenames in os.walk(PROJECT_DIR):
    for filename in filenames:
        file_path = os.path.join(root, filename)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()[:5000]  # 5k znakov = dosť pre kód
        files.append(file_path)
        embeddings.append(model.encode(content))

# 4. BUILDOVANIE FAISS INDEXU (pre rýchlu search)
embedding_dim = len(embeddings[0])
index = faiss.IndexFlatL2(embedding_dim)
index.add(np.array(embeddings))

# 5. DETEKCIJA ORPHANED/DUPLIKÁTOV
orphaned = []
duplicates = []
for i, file in enumerate(files):
    # Hľadaj najbližšie súbory (k=2 = vylúči sám seba)
    distances, indices = index.search(np.array([embeddings[i]]), k=2)
    similarity = 1 - (distances[0][1] / 2)  # L2 -> cosine
    
    # ORPHANED: Nízka podobnosť s ostatnými súbormi
    if similarity < SIMILARITY_THRESHOLD:
        orphaned.append(file)
    
    # DUPLIKÁT: Vysoká podobnosť s iným súborom
    elif similarity > 0.95:
        duplicates.append((file, files[indices[0][1]]))

# 6. VÝSLEDKY (vypíš do konzoly alebo do súboru)
print(f"Orphaned files ({len(orphaned)}):", orphaned)
print(f"Duplicates ({len(duplicates)}):", duplicates)