import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import sqlite3
from config import DATABASE_PATH, MODEL_PATH, DATASET_CSV

def build_dataset():
    """
    Ambil data dari database dan bentuk DataFrame untuk training.
    Setiap baris = satu move dari satu game.
    Kolom: centipawn_loss, engine_similarity, move_entropy, tactical_spike, label (Human/Engine)
    """
    conn = sqlite3.connect(DATABASE_PATH)
    query = """
    SELECT mf.centipawn_loss, mf.engine_similarity, mf.move_entropy, mf.tactical_spike,
           g.white_label as label
    FROM move_features mf
    JOIN games g ON mf.game_id = g.id
    WHERE mf.side = 'white'
    UNION ALL
    SELECT mf.centipawn_loss, mf.engine_similarity, mf.move_entropy, mf.tactical_spike,
           g.black_label as label
    FROM move_features mf
    JOIN games g ON mf.game_id = g.id
    WHERE mf.side = 'black'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    # Encoding label: Human -> 0, Engine -> 1
    df['label'] = df['label'].map({'Human': 0, 'Engine': 1})
    df.dropna(inplace=True)
    df.to_csv(DATASET_CSV, index=False)
    return df

def train_model():
    """Latih RandomForest dari dataset."""
    df = build_dataset()
    if df.empty:
        print("Dataset kosong. Jalankan beberapa simulasi arena dulu.")
        return None
    X = df[['centipawn_loss', 'engine_similarity', 'move_entropy', 'tactical_spike']]
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(
        n_estimators=150,
        random_state=42,
        class_weight={0: 1, 1: 2}   # memberi bobot 2x untuk kelas Engine
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=['Human', 'Engine']))
    joblib.dump(model, MODEL_PATH)
    print(f"Model disimpan di {MODEL_PATH}")
    return model

def load_model():
    try:
        return joblib.load(MODEL_PATH)
    except:
        return None

def predict_move(move_features, model=None):
    """Prediksi satu move: [centipawn_loss, engine_similarity, entropy, tactical_spike]"""
    if model is None:
        model = load_model()
    if model is None:
        return "No model", np.array([0.0, 0.0])
    # Gunakan DataFrame agar sesuai dengan feature names saat training
    feat_df = pd.DataFrame(
        [move_features],
        columns=['centipawn_loss', 'engine_similarity', 'move_entropy', 'tactical_spike']
    )
    proba = model.predict_proba(feat_df)[0]
    pred = model.predict(feat_df)[0]
    label = 'Engine-like' if pred == 1 else 'Human'
    return label, proba