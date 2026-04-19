import { create } from "zustand";
import { persist } from "zustand/middleware";

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

  onboardingStep: number;
  setOnboardingStep: (s: number) => void;

  profileId: string;
  setProfileId: (id: string) => void;

  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;

  preferences: Preferences;
  setPreferences: (p: Partial<Preferences>) => void;

  selectedFoods: FoodItem[];
  setSelectedFoods: (f: FoodItem[]) => void;

  mealPlanResponse: string;
  groceryResponse: string;
  setResponse: (key: "mealPlan" | "grocery", text: string) => void;

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

export const useApp = create<AppState>()(
  persist(
    (set) => ({
      screen: 1,
      setScreen: (s) => set({ screen: s }),

      onboardingStep: 1,
      setOnboardingStep: (s) => set({ onboardingStep: s }),

      profileId: "",
      setProfileId: (id) => set({ profileId: id }),

      profile: emptyProfile,
      setProfile: (p) => set((st) => ({ profile: { ...st.profile, ...p } })),

      preferences: emptyPrefs,
      setPreferences: (p) => set((st) => ({ preferences: { ...st.preferences, ...p } })),

      selectedFoods: [],
      setSelectedFoods: (f) => set({ selectedFoods: f }),

      mealPlanResponse: "",
      groceryResponse: "",
      setResponse: (key, text) => set(() => {
        const map = { mealPlan: "mealPlanResponse", grocery: "groceryResponse" } as const;
        return { [map[key]]: text } as Partial<AppState>;
      }),

      reset: () => set({
        screen: 1,
        onboardingStep: 1,
        profileId: "",
        profile: emptyProfile,
        preferences: emptyPrefs,
        selectedFoods: [],
        mealPlanResponse: "",
        groceryResponse: "",
      }),
    }),
    {
      name: "foodbridge-state",
      partialize: (s) => ({
        screen: s.screen,
        onboardingStep: s.onboardingStep,
        profileId: s.profileId,
        profile: s.profile,
        preferences: s.preferences,
      }),
    },
  ),
);