import { useState, useCallback } from 'react';
import type { Screen, NavigationState } from '../state/navigation.js';
import { createInitialState, navigate, goBack } from '../state/navigation.js';

export function useNavigation() {
  const [state, setState] = useState<NavigationState>(createInitialState());

  const navigateTo = useCallback((screen: Screen, groupContext?: string) => {
    setState(prev => navigate(prev, screen, groupContext));
  }, []);

  const back = useCallback(() => {
    setState(prev => goBack(prev));
  }, []);

  const currentScreen = state.currentScreen;
  const previousScreen = state.previousScreen;
  const groupContext = state.groupContext;

  return {
    currentScreen,
    previousScreen,
    groupContext,
    navigateTo,
    back,
  };
}
