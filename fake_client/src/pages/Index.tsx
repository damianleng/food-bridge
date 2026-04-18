import { useApp } from "@/store/app";
import Onboarding from "@/screens/Onboarding";
import Preferences from "@/screens/Preferences";
import FoodSearch from "@/screens/FoodSearch";
import MealPlan from "@/screens/MealPlan";
import GroceryList from "@/screens/GroceryList";

const Index = () => {
  const screen = useApp((s) => s.screen);

  return (
    <div className="bg-background text-foreground min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-foreground text-background px-3 py-1 text-xs">Skip to content</a>
      <div className="border-b border-foreground">
        <div className="max-w-xl mx-auto px-5 py-3 flex items-center justify-between">
          <span className="font-extrabold tracking-tight text-base">FOODBRIDGE</span>
          <span className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Nutrition · Plan · Shop</span>
        </div>
      </div>
      <main id="main">
        {screen === 1 && <Onboarding />}
        {screen === 2 && <Preferences />}
        {screen === 3 && <FoodSearch />}
        {screen === 4 && <MealPlan />}
        {screen === 5 && <GroceryList />}
      </main>
    </div>
  );
};

export default Index;
