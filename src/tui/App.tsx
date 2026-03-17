import { useState } from 'react';
import { Box, Text } from 'ink';
import { MainMenu } from './screens/MainMenu.js';
import { SystemStatus } from './screens/SystemStatus.js';
import { Configuration } from './screens/Configuration.js';
import { GroupManagement } from './screens/GroupManagement.js';
import { GroupEdit } from './screens/GroupEdit.js';
import { Sources } from './screens/Sources.js';
import { FeverAPI } from './screens/FeverAPI.js';
import { LLMDebug } from './screens/LLMDebug.js';
import { TTSDebug } from './screens/TTSDebug.js';
import { Generation } from './screens/Generation.js';

type Screen = 'main' | 'system' | 'config' | 'groups' | 'groupEdit' | 'sources' | 'fever' | 'llm' | 'tts' | 'generation';

export function App({ initialGroupId }: { initialGroupId?: string }) {
  const [screen, setScreen] = useState<Screen>('main');
  const [editGroupId, setEditGroupId] = useState<string | undefined>(initialGroupId);

  const handleMainMenuSelect = (index: number) => {
    const screens: Screen[] = ['system', 'config', 'groups', 'sources', 'fever', 'llm', 'tts', 'generation'];
    const targetScreen = screens[index];
    if (targetScreen) {
      setScreen(targetScreen);
    }
  };

  const handleBack = () => {
    if (screen === 'groupEdit') {
      setScreen('groups');
    } else {
      setScreen('main');
    }
  };

  const handleEditGroup = (groupId: string) => {
    setEditGroupId(groupId);
    setScreen('groupEdit');
  };

  const handleExit = () => {
    process.exit(0);
  };

  return (
    <Box flexDirection="column">
      <Box marginBottom={1}>
        <Text bold>RSS2Pod TUI v3.0.0</Text>
      </Box>
      {screen === 'main' && <MainMenu onExit={handleExit} onSelect={handleMainMenuSelect} />}
      {screen === 'system' && <SystemStatus onBack={handleBack} />}
      {screen === 'config' && <Configuration onBack={handleBack} />}
      {screen === 'groups' && <GroupManagement onBack={handleBack} onEdit={handleEditGroup} />}
      {screen === 'groupEdit' && editGroupId && <GroupEdit groupId={editGroupId} onBack={handleBack} />}
      {screen === 'sources' && <Sources onBack={handleBack} />}
      {screen === 'fever' && <FeverAPI onBack={handleBack} />}
      {screen === 'llm' && <LLMDebug onBack={handleBack} />}
      {screen === 'tts' && <TTSDebug onBack={handleBack} />}
      {screen === 'generation' && <Generation onBack={handleBack} />}
    </Box>
  );
}
