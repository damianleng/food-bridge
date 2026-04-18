"""SQLAlchemy ORM models for FoodBridge — USDA FoodData Central + user tables."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, Integer, Numeric, Date, DateTime, Text, String,
    ForeignKey, BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Reference / Lookup ────────────────────────────────────────────────────────

class FoodCategory(Base):
    __tablename__ = "food_category"
    id = Column(Integer, primary_key=True)
    code = Column(String(10))
    description = Column(Text)


class WweiaFoodCategory(Base):
    __tablename__ = "wweia_food_category"
    wweia_food_category = Column(Integer, primary_key=True)
    wweia_food_category_description = Column(Text)


class Nutrient(Base):
    __tablename__ = "nutrient"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    unit_name = Column(String(20))
    nutrient_nbr = Column(Numeric)
    rank = Column(Numeric)


class FoodNutrientDerivation(Base):
    __tablename__ = "food_nutrient_derivation"
    id = Column(Integer, primary_key=True)
    code = Column(String(10))
    description = Column(Text)


class FoodNutrientSource(Base):
    __tablename__ = "food_nutrient_source"
    id = Column(Integer, primary_key=True)
    code = Column(String(10))
    description = Column(Text)


class FoodAttributeType(Base):
    __tablename__ = "food_attribute_type"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    description = Column(Text)


class MeasureUnit(Base):
    __tablename__ = "measure_unit"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class LabMethod(Base):
    __tablename__ = "lab_method"
    id = Column(Integer, primary_key=True)
    description = Column(Text)
    technique = Column(String(50))


class RetentionFactor(Base):
    __tablename__ = "retention_factor"
    gid = Column(Integer, primary_key=True)
    code = Column(Integer)
    food_group_id = Column(Integer)
    description = Column(Text)


class FnddsDerivation(Base):
    __tablename__ = "fndds_derivation"
    derivation_code = Column(String(10), primary_key=True)
    derivation_description = Column(Text)


# ── Core Food ─────────────────────────────────────────────────────────────────

class Food(Base):
    __tablename__ = "food"
    fdc_id = Column(Integer, primary_key=True)
    data_type = Column(String(50))
    description = Column(Text)
    food_category_id = Column(Text)   # text label in branded exports
    publication_date = Column(Date)


# ── Food-Dependent Tables ─────────────────────────────────────────────────────

class BrandedFood(Base):
    __tablename__ = "branded_food"
    fdc_id = Column(Integer, primary_key=True)
    brand_owner = Column(Text)
    brand_name = Column(Text)
    subbrand_name = Column(Text)
    gtin_upc = Column(String(20))
    ingredients = Column(Text)
    not_a_significant_source_of = Column(Text)
    serving_size = Column(Numeric)
    serving_size_unit = Column(String(20))
    household_serving_fulltext = Column(Text)
    branded_food_category = Column(Text)
    data_source = Column(String(20))
    package_weight = Column(Text)
    modified_date = Column(Date)
    available_date = Column(Date)
    market_country = Column(Text)
    discontinued_date = Column(Date)
    preparation_state_code = Column(Text)
    trade_channel = Column(Text)
    short_description = Column(Text)
    material_code = Column(Text)


class FoodNutrient(Base):
    __tablename__ = "food_nutrient"
    id = Column(BigInteger, primary_key=True)
    fdc_id = Column(Integer)
    nutrient_id = Column(Integer)
    amount = Column(Numeric)
    data_points = Column(Integer)
    derivation_id = Column(Integer)
    min = Column(Numeric)
    max = Column(Numeric)
    median = Column(Numeric)
    loq = Column(Numeric)
    footnote = Column(Text)
    min_year_acquired = Column(Integer)
    percent_daily_value = Column(Numeric)


class FoodAttribute(Base):
    __tablename__ = "food_attribute"
    id = Column(BigInteger, primary_key=True)
    fdc_id = Column(Integer)
    seq_num = Column(Integer)
    food_attribute_type_id = Column(Integer)
    name = Column(Text)
    value = Column(Text)


class FoodPortion(Base):
    __tablename__ = "food_portion"
    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer)
    seq_num = Column(Integer)
    amount = Column(Numeric)
    measure_unit_id = Column(Integer)
    portion_description = Column(Text)
    modifier = Column(Text)
    gram_weight = Column(Numeric)
    data_points = Column(Integer)
    footnote = Column(Text)
    min_year_acquired = Column(Integer)


class FoodComponent(Base):
    __tablename__ = "food_component"
    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer)
    name = Column(Text)
    pct_weight = Column(Numeric)
    is_refuse = Column(String(1))
    gram_weight = Column(Numeric)
    data_points = Column(Integer)
    min_year_acquired = Column(Integer)


class FoodNutrientConversionFactor(Base):
    __tablename__ = "food_nutrient_conversion_factor"
    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer)


class FoodCalorieConversionFactor(Base):
    __tablename__ = "food_calorie_conversion_factor"
    food_nutrient_conversion_factor_id = Column(Integer, primary_key=True)
    protein_value = Column(Numeric)
    fat_value = Column(Numeric)
    carbohydrate_value = Column(Numeric)


class FoodProteinConversionFactor(Base):
    __tablename__ = "food_protein_conversion_factor"
    food_nutrient_conversion_factor_id = Column(Integer, primary_key=True)
    value = Column(Numeric)


class FoodUpdateLogEntry(Base):
    __tablename__ = "food_update_log_entry"
    id = Column(BigInteger, primary_key=True)
    description = Column(Text)
    last_updated = Column(Date)


class SurveyFnddsFood(Base):
    __tablename__ = "survey_fndds_food"
    fdc_id = Column(Integer, primary_key=True)
    food_code = Column(String(20))
    wweia_category_code = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)


class InputFood(Base):
    __tablename__ = "input_food"
    id = Column(Integer, primary_key=True)
    fdc_id = Column(Integer)
    fdc_id_of_input_food = Column(Integer)
    seq_num = Column(Integer)
    amount = Column(Numeric)
    sr_code = Column(Integer)
    sr_description = Column(Text)
    unit = Column(String(20))
    portion_code = Column(String(20))
    portion_description = Column(Text)
    gram_weight = Column(Numeric)
    retention_code = Column(Integer)


class FnddsIngredientNutrientValue(Base):
    __tablename__ = "fndds_ingredient_nutrient_value"
    # Composite PK: ingredient × nutrient × date range
    ingredient_code = Column(Integer, primary_key=True)
    nutrient_code = Column(Integer, primary_key=True)
    start_date = Column(Date, primary_key=True)
    ingredient_description = Column(Text)
    nutrient_value = Column(Numeric)
    nutrient_value_source = Column(Text)
    fdc_id = Column(Integer)
    derivation_code = Column(String(10))
    sr_addmod_year = Column(Integer)
    foundation_year_acquired = Column(Integer)
    end_date = Column(Date)


class FoundationFood(Base):
    __tablename__ = "foundation_food"
    fdc_id = Column(Integer, primary_key=True)
    ndb_number = Column(Integer)
    footnote = Column(Text)


class SrLegacyFood(Base):
    __tablename__ = "sr_legacy_food"
    fdc_id = Column(Integer, primary_key=True)
    ndb_number = Column(Integer)


class SampleFood(Base):
    __tablename__ = "sample_food"
    fdc_id = Column(Integer, primary_key=True)


class SubSampleFood(Base):
    __tablename__ = "sub_sample_food"
    fdc_id = Column(Integer, primary_key=True)
    fdc_id_of_sample_food = Column(Integer)


class AcquisitionSamples(Base):
    __tablename__ = "acquisition_samples"
    fdc_id_of_sample_food = Column(Integer, primary_key=True)
    fdc_id_of_acquisition_food = Column(Integer, primary_key=True)


class MarketAcquisition(Base):
    __tablename__ = "market_acquisition"
    fdc_id = Column(Integer, primary_key=True)
    brand_description = Column(Text)
    expiration_date = Column(Date)
    label_weight = Column(Text)
    location = Column(Text)
    acquisition_date = Column(Date)
    sales_type = Column(Text)
    sample_lot_nbr = Column(Text)
    sell_by_date = Column(Date)
    store_city = Column(Text)
    store_name = Column(Text)
    store_state = Column(String(5))
    upc_code = Column(Text)
    acquisition_number = Column(Text)


class AgriculturalSamples(Base):
    __tablename__ = "agricultural_samples"
    fdc_id = Column(Integer, primary_key=True)
    acquisition_date = Column(Date)
    market_class = Column(Text)
    treatment = Column(Text)
    state = Column(String(5))


class LabMethodCode(Base):
    __tablename__ = "lab_method_code"
    lab_method_id = Column(Integer, primary_key=True)
    code = Column(String(20), primary_key=True)


class LabMethodNutrient(Base):
    __tablename__ = "lab_method_nutrient"
    lab_method_id = Column(Integer, primary_key=True)
    nutrient_id = Column(Integer, primary_key=True)


class SubSampleResult(Base):
    __tablename__ = "sub_sample_result"
    food_nutrient_id = Column(BigInteger, primary_key=True)
    adjusted_amount = Column(Numeric)
    lab_method_id = Column(Integer)
    nutrient_name = Column(Text)


class Microbe(Base):
    __tablename__ = "microbe"
    id = Column(Integer, primary_key=True)
    food_id = Column(Integer)
    method = Column(Text)
    microbe_code = Column(Text)
    min_value = Column(Numeric)
    max_value = Column(Numeric)
    uom = Column(String(20))


# ── User Tables ───────────────────────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profile"
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    height_cm = Column(Numeric)
    weight_kg = Column(Numeric)
    age = Column(Integer)
    sex = Column(String(10))
    activity_level = Column(String(30))
    smoking_status = Column(String(20))
    pregnancy_status = Column(String(20))
    household_size_adults = Column(Integer)
    household_size_children = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    health_goals = relationship("UserHealthGoal", back_populates="profile", cascade="all, delete-orphan")
    health_conditions = relationship("UserHealthCondition", back_populates="profile", cascade="all, delete-orphan")
    medications = relationship("UserMedication", back_populates="profile", cascade="all, delete-orphan")
    grocery_preference = relationship("UserGroceryPreference", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    dietary_preferences = relationship("UserDietaryPreference", back_populates="profile", cascade="all, delete-orphan")
    allergies = relationship("UserAllergy", back_populates="profile", cascade="all, delete-orphan")
    cuisine_preferences = relationship("UserCuisinePreference", back_populates="profile", cascade="all, delete-orphan")
    calculated_dvs = relationship("UserCalculatedDV", back_populates="profile", cascade="all, delete-orphan")


class UserHealthGoal(Base):
    __tablename__ = "user_health_goal"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False)
    goal = Column(Text, nullable=False)
    profile = relationship("UserProfile", back_populates="health_goals")


class UserHealthCondition(Base):
    __tablename__ = "user_health_condition"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False)
    condition_name = Column(Text, nullable=False)
    profile = relationship("UserProfile", back_populates="health_conditions")


class UserMedication(Base):
    __tablename__ = "user_medication"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False)
    rxcui = Column(String(20))
    medication_name = Column(Text)
    drug_class = Column(Text)
    profile = relationship("UserProfile", back_populates="medications")


class UserGroceryPreference(Base):
    __tablename__ = "user_grocery_preference"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False, unique=True)
    weekly_budget_usd = Column(Numeric(10, 2))
    zip_code = Column(String(10))
    wic_filter_active = Column(String(1))  # Y/N, derived from profile
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile = relationship("UserProfile", back_populates="grocery_preference")


class UserDietaryPreference(Base):
    __tablename__ = "user_dietary_preference"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False)
    preference = Column(Text, nullable=False)
    profile = relationship("UserProfile", back_populates="dietary_preferences")


class UserAllergy(Base):
    __tablename__ = "user_allergy"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False)
    allergen = Column(Text, nullable=False)
    profile = relationship("UserProfile", back_populates="allergies")


class UserCuisinePreference(Base):
    __tablename__ = "user_cuisine_preference"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False)
    cuisine = Column(Text, nullable=False)
    profile = relationship("UserProfile", back_populates="cuisine_preferences")


class UserCalculatedDV(Base):
    __tablename__ = "user_calculated_dv"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.profile_id", ondelete="CASCADE"), nullable=False)
    calories_kcal = Column(Numeric)
    protein_g = Column(Numeric)
    fat_g = Column(Numeric)
    saturated_fat_g = Column(Numeric)
    carbohydrates_g = Column(Numeric)
    fiber_g = Column(Numeric)
    added_sugars_g = Column(Numeric)
    sodium_mg = Column(Numeric)
    potassium_mg = Column(Numeric)
    calcium_mg = Column(Numeric)
    iron_mg = Column(Numeric)
    vitamin_c_mg = Column(Numeric)
    vitamin_d_iu = Column(Numeric)
    folate_mcg = Column(Numeric)
    b12_mcg = Column(Numeric)
    magnesium_mg = Column(Numeric)
    zinc_mg = Column(Numeric)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    profile = relationship("UserProfile", back_populates="calculated_dvs")
