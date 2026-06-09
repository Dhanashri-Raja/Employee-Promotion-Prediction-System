import pandas as pd
import pickle

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


# -----------------------------------
# Load Dataset
# -----------------------------------
df = pd.read_csv("employee_promotions.csv")

# Use smaller sample (FAST TRAINING)
df = df.sample(20000, random_state=42)


# -----------------------------------
# Features and Target
# -----------------------------------
features = [
    "department",
    "education",
    "gender",
    "no_of_trainings",
    "age",
    "previous_year_rating",
    "length_of_service",
    "awards_won",
    "avg_training_score"
]

target = "is_promoted"

df = df[features + [target]]

# Clean missing values
df = df.dropna()


# -----------------------------------
# Split X and y
# -----------------------------------
X = df[features]
y = df[target]


# -----------------------------------
# Column Types
# -----------------------------------
categorical_cols = ["department", "education", "gender"]

numerical_cols = [
    "no_of_trainings",
    "age",
    "previous_year_rating",
    "length_of_service",
    "awards_won",
    "avg_training_score"
]


# -----------------------------------
# Preprocessing
# -----------------------------------
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numerical_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols)
    ]
)


# -----------------------------------
# Fast Model (Logistic Regression)
# -----------------------------------
model = Pipeline(steps=[
    ("preprocessing", preprocessor),
    ("classifier", LogisticRegression(max_iter=1000))
])


# -----------------------------------
# Train Test Split
# -----------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# -----------------------------------
# Train Model
# -----------------------------------
print("Training model...")

model.fit(X_train, y_train)


# -----------------------------------
# Evaluate
# -----------------------------------
y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("Model Accuracy:", accuracy)


# -----------------------------------
# Save Model
# -----------------------------------
with open("attr.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model saved successfully as attr.pkl")