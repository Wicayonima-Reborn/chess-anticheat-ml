import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import sqlite3
from config import DATABASE_PATH, MODEL_PATH, DATASET_CSV

def build_dataset():
    """Extract labeled move features from the SQLite database."""
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
    df['label'] = df['label'].map({'Human': 0, 'Engine': 1})
    df.dropna(inplace=True)
    df.to_csv(DATASET_CSV, index=False)
    return df

def train_model():
    """Train a Random Forest classifier and save the model."""
    df = build_dataset()
    if df.empty:
        print("Empty dataset. Run simulations first.")
        return None
    X = df[['centipawn_loss', 'engine_similarity', 'move_entropy', 'tactical_spike']]
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(
        n_estimators=150,
        random_state=42,
        class_weight={0: 1, 1: 2}   # upweight engine class to reduce false negatives
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=['Human', 'Engine']))
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return model

def load_model():
    """Load the trained model from disk."""
    try:
        return joblib.load(MODEL_PATH)
    except:
        return None

def predict_move(move_features, model=None):
    """
    Predict a single move given its features.
    Returns (label, probability array).
    """
    if model is None:
        model = load_model()
    if model is None:
        return "No model", np.array([0.0, 0.0])
    # Wrap in DataFrame to match the feature names the model was trained on
    feat_df = pd.DataFrame(
        [move_features],
        columns=['centipawn_loss', 'engine_similarity', 'move_entropy', 'tactical_spike']
    )
    proba = model.predict_proba(feat_df)[0]
    pred = model.predict(feat_df)[0]
    label = 'Engine-like' if pred == 1 else 'Human'
    return label, proba
