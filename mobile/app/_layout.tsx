import { Stack } from 'expo-router';
import { HistoryProvider } from '../hooks/useHistory';
import { SettingsProvider } from '../hooks/useSettings';
import { Platform, View, useWindowDimensions } from 'react-native';

function AppShell() {
  const { width } = useWindowDimensions();
  const isDesktop = Platform.OS === 'web' && width >= 768;

  const stack = (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="location" />
      <Stack.Screen name="vehicle" />
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="sos" options={{ presentation: 'modal' }} />
    </Stack>
  );

  if (Platform.OS !== 'web' || isDesktop) {
    return <View style={{ flex: 1 }}>{stack}</View>;
  }

  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#e5e7eb', paddingVertical: 40 }}>
      <View style={{
        width: '100%',
        maxWidth: 420,
        height: '100%',
        maxHeight: 850,
        backgroundColor: '#fff',
        overflow: 'hidden',
        borderRadius: 30,
        borderWidth: 8,
        borderColor: '#1f2937',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
      } as any}>
        {stack}
      </View>
    </View>
  );
}

export default function RootLayout() {
  return (
    <SettingsProvider>
      <HistoryProvider>
        {Platform.OS === 'web' && (
          <style dangerouslySetInnerHTML={{ __html: `
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;600;800&family=Playfair+Display:ital,wght@0,400;0,600;1,400;1,600&display=swap');
            body, input, button, textarea { font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important; }
            h1, h2, h3, .logo-text, [data-testid="logo"] { font-family: 'Outfit', sans-serif !important; }
            @media (max-width: 767px) { body { background-color: #e5e7eb !important; } }
            @media (min-width: 768px) { body { background-color: #FBF7F0 !important; } }
          `}} />
        )}
        <AppShell />
      </HistoryProvider>
    </SettingsProvider>
  );
}
