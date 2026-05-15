import { Stack } from 'expo-router';

export default function ZonesLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="live" />
      <Stack.Screen name="speed-limits" />
    </Stack>
  );
}
