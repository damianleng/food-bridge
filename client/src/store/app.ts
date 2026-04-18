import { create } from "zustand";

export type Sex = "Male" | "Female";
export type Activity = "Sedentary" | "Lightly Active" | "Moderately Active" | "Very Active" | "Extra Active";
export type Smoking = "Smoker" | "Non-Smoker" | "Former Smoker";

export interface Profile {
  height: string;
  weight: string;
  age: string;
  sex: Sex | "";
  activity: Activity | "";
  goals: string[];
  conditions: string[];
  smoking: Smoking | "";
  medications: string[];
  adults: number;
  children: number;
}

export interface Preferences {
  budget: string;
  zip: string;
  diet: string[];
  allergies: string[];
  cuisines: string[];
  wic: boolean;
}

export interface FoodItem {
  fdc_id?: string | number;
  name: string;
  data_type?: string;
  score?: number;
  top_nutrients?: string[];
}

export type Screen = 1 | 2 | 3 | 4 | 5;

interface AppState {
  screen: Screen;
  setScreen: (s: Screen) => void;

  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;

  preferences: Preferences;
  setPreferences: (p: Partial<Preferences>) => void;

  selectedFoods: FoodItem[];
  setSelectedFoods: (f: FoodItem[]) => void;

  // raw assistant text per step
  profileResponse: string;
  preferencesResponse: string;
  mealPlanResponse: string;
  groceryResponse: string;
  setResponse: (key: "profile" | "preferences" | "mealPlan" | "grocery", text: string) => void;

  reset: () => void;
}

const emptyProfile: Profile = {
  height: "", weight: "", age: "", sex: "", activity: "",
  goals: [], conditions: [], smoking: "", medications: [],
  adults: 1, children: 0,
};

const emptyPrefs: Preferences = {
  budget: "", zip: "", diet: [], allergies: [], cuisines: [], wic: false,
};

export const useApp = create<AppState>((set) => ({
  screen: 1,
  setScreen: (s) => set({ screen: s }),

  profile: emptyProfile,
  setProfile: (p) => set((st) => ({ profile: { ...st.profile, ...p } })),

  preferences: emptyPrefs,
  setPreferences: (p) => set((st) => ({ preferences: { ...st.preferences, ...p } })),

  selectedFoods: [],
  setSelectedFoods: (f) => set({ selectedFoods: f }),

  profileResponse: "",
  preferencesResponse: "",
  mealPlanResponse: "",
  groceryResponse: "",
  setResponse: (key, text) => set(() => {
    const map = {
      profile: "profileResponse",
      preferences: "preferencesResponse",
      mealPlan: "mealPlanResponse",
      grocery: "groceryResponse",
    } as const;
    return { [map[key]]: text } as Partial<AppState>;
  }),

  reset: () => set({
    screen: 1,
    profile: emptyProfile,
    preferences: emptyPrefs,
    selectedFoods: [],
    profileResponse: "",
    preferencesResponse: "",
    mealPlanResponse: "",
    groceryResponse: "",
  }),
}));
