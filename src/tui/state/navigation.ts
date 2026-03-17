// Navigation state types and utilities

export type Screen = 
  | 'main'
  | 'system'
  | 'config'
  | 'groups'
  | 'group-detail'
  | 'sources'
  | 'fever'
  | 'llm'
  | 'tts'
  | 'generation'
  | 'pipeline-run';

export interface NavigationState {
  currentScreen: Screen;
  previousScreen: Screen | null;
  groupContext?: string; // Current group ID when in group-specific screens
}

export function createInitialState(): NavigationState {
  return {
    currentScreen: 'main',
    previousScreen: null,
  };
}

export function navigate(state: NavigationState, screen: Screen, groupContext?: string): NavigationState {
  return {
    currentScreen: screen,
    previousScreen: state.currentScreen,
    groupContext,
  };
}

export function goBack(state: NavigationState): NavigationState {
  if (!state.previousScreen) {
    return state;
  }
  
  return {
    currentScreen: state.previousScreen,
    previousScreen: 'main',
    groupContext: undefined,
  };
}
