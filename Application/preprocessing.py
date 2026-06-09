from typing import Tuple, List
import logging
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


FEATURES: List[str] = [
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

TARGET: str = "is_promoted"

CATEGORICAL_COLS: List[str] = [
    "department",
    "education",
    "gender"
]

NUMERICAL_COLS: List[str] = [
    "no_of_trainings",
    "age",
    "previous_year_rating",
    "length_of_service",
    "awards_won",
    "avg_training_score"
]

def validate_columns(df: pd.DataFrame) -> None:
    missing_cols = set(FEATURES + [TARGET]) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    

    df = df.copy()

    df["training_efficiency"] = (
        df["avg_training_score"] / (df["no_of_trainings"] + 1)
    )

    return df


def clean_data(df: pd.DataFrame, drop_missing: bool = False) -> pd.DataFrame:
   

    logger.info("Starting data cleaning...")

    validate_columns(df)

    df = df[FEATURES + [TARGET]].copy()

    if drop_missing:
        logger.warning("Dropping rows with missing values.")
        df = df.dropna()

    df = feature_engineering(df)

    logger.info("Data cleaning completed.")

    return df


def get_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                )
            )
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, NUMERICAL_COLS),
            ("cat", categorical_pipeline, CATEGORICAL_COLS)
        ],
        remainder="drop"
    )

    return preprocessor

def split_features_target(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.Series]:
    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    return X, y