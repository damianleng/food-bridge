import React from "react";
import { useApp } from "@/store/app";
import Onboarding from "@/screens/Onboarding";
import Preferences from "@/screens/Preferences";
import FoodSearch from "@/screens/FoodSearch";
import MealPlan from "@/screens/MealPlan";
import GroceryList from "@/screens/GroceryList";

const SCREEN_LABELS = ["Health Profile", "Preferences", "Find Foods", "Meal Plan", "Grocery List"];

export default function Home() {
  const screen = useApp((s) => s.screen);

  return (
    <div className="min-h-screen">
      {/* Emerald gradient header */}
      <header className="bg-gradient-to-br from-emerald-700 via-emerald-600 to-teal-500 text-white shadow-lg">
        <div className="max-w-xl mx-auto px-5 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🌿</span>
              <span className="text-xl font-extrabold tracking-tight">FoodBridge</span>
            </div>
            <span className="text-xs text-emerald-200 uppercase tracking-widest hidden sm:block">
              Nutrition · Plan · Shop
            </span>
          </div>

          {/* Step indicator */}
          <div className="flex items-center mt-4">
            {SCREEN_LABELS.map((label, i) => {
              const num = i + 1;
              const active = screen === num;
              const done = screen > num;
              return (
                <React.Fragment key={label}>
                  <div className="flex flex-col items-center gap-1">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all
                      ${done ? "bg-white text-emerald-700 border-white"
                        : active ? "bg-amber-400 text-white border-amber-300 scale-110 shadow-lg"
                        : "bg-white/20 text-white/60 border-white/30"}`}>
                      <span className="leading-none">{done ? "✓" : num}</span>
                    </div>
                    <span className={`text-[10px] font-medium text-center leading-tight hidden sm:block
                      ${active ? "text-amber-300" : "text-emerald-200"}`}>
                      {label}
                    </span>
                  </div>
                  {i < SCREEN_LABELS.length - 1 && (
                    <div className={`flex-1 h-0.5 mb-4 mx-1 transition-all ${done ? "bg-white" : "bg-white/25"}`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </header>

      <main>
        {screen === 1 && <Onboarding />}
        {screen === 2 && <Preferences />}
        {screen === 3 && <FoodSearch />}
        {screen === 4 && <MealPlan />}
        {screen === 5 && <GroceryList />}
      </main>
    </div>
  );
}