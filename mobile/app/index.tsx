import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, Platform, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';

export default function OnboardingScreen() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isDesktop = Platform.OS === 'web' && width >= 768;

  if (isDesktop) {
    return (
      <View style={desktop.container}>
        <StatusBar style="light" />

        {/* Left content panel */}
        <View style={desktop.leftPanel}>
          <View style={shared.logoContainer}>
            <View style={shared.logoIcon}>
              <Text style={shared.logoIconText}>DL</Text>
            </View>
            <Text style={shared.logoText}>DriveLegal</Text>
          </View>

          <View style={desktop.body}>
            <Text style={desktop.headline}>
              Know the rules,{'\n'}wherever you{' '}
              <Text style={shared.italicHighlight}>drive.</Text>
            </Text>
            <Text style={desktop.subheadline}>
              Plain-language traffic laws, fines and rights — for your exact street, in your language.
            </Text>
          </View>

          <View style={desktop.footer}>
            <TouchableOpacity
              style={desktop.primaryButton}
              onPress={() => router.push('/location')}
            >
              <Text style={shared.primaryButtonText}>Get started</Text>
              <Ionicons name="arrow-forward" size={20} color="#fff" style={shared.buttonIcon} />
            </TouchableOpacity>

            <View style={shared.signInRow}>
              <Text style={shared.signInText}>Already have an account? </Text>
              <TouchableOpacity onPress={() => router.push('/(tabs)')}>
                <Text style={shared.signInLink}>Sign in</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* Right decorative panel */}
        <View style={desktop.rightPanel}>
          <View style={desktop.bigLogoWrap}>
            <Text style={desktop.bigLogoText}>DL</Text>
          </View>
          <Text style={desktop.rightTagline}>Drive informed.{'\n'}Stay protected.</Text>
        </View>
      </View>
    );
  }

  return (
    <SafeAreaView style={mobile.container}>
      <StatusBar style="dark" />
      <View style={mobile.content}>

        <View style={shared.logoContainer}>
          <View style={shared.logoIcon}>
            <Text style={shared.logoIconText}>DL</Text>
          </View>
          <Text style={shared.logoText}>DriveLegal</Text>
        </View>

        <View style={mobile.mainBody}>
          <Text style={mobile.headline}>
            Know the rules,{'\n'}wherever you <Text style={shared.italicHighlight}>drive.</Text>
          </Text>
          <Text style={mobile.subheadline}>
            Plain-language traffic laws, fines and rights — for your exact street, in your language.
          </Text>
        </View>

        <View style={mobile.footer}>
          <TouchableOpacity
            style={mobile.primaryButton}
            onPress={() => router.push('/location')}
          >
            <Text style={shared.primaryButtonText}>Get started</Text>
            <Ionicons name="arrow-forward" size={18} color="#fff" style={shared.buttonIcon} />
          </TouchableOpacity>

          <View style={shared.signInRow}>
            <Text style={shared.signInText}>Already have an account? </Text>
            <TouchableOpacity onPress={() => router.push('/(tabs)')}>
              <Text style={shared.signInLink}>Sign in</Text>
            </TouchableOpacity>
          </View>
        </View>

      </View>
    </SafeAreaView>
  );
}

const shared = StyleSheet.create({
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logoIcon: {
    width: 32,
    height: 32,
    backgroundColor: '#1B1A17',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  logoIconText: {
    color: '#C9621D',
    fontWeight: '700',
    fontSize: 14,
  },
  logoText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? 'Outfit, sans-serif' : 'System',
    letterSpacing: -0.5,
  },
  italicHighlight: {
    color: '#C9621D',
    fontStyle: 'italic',
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  buttonIcon: {
    marginLeft: 8,
  },
  signInRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  signInText: {
    color: '#6b7280',
    fontSize: 14,
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  signInLink: {
    color: '#C9621D',
    fontSize: 14,
    fontWeight: '600',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
});

const desktop = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#FBF7F0',
  },
  leftPanel: {
    flex: 1,
    paddingHorizontal: 80,
    paddingVertical: 64,
    justifyContent: 'space-between',
  },
  body: {
    flex: 1,
    justifyContent: 'center',
  },
  headline: {
    fontSize: 64,
    lineHeight: 72,
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? '"Playfair Display", serif' : 'serif',
    marginBottom: 28,
    letterSpacing: -2,
  },
  subheadline: {
    fontSize: 18,
    lineHeight: 28,
    color: '#4b5563',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
    maxWidth: 460,
  },
  footer: {
    gap: 0,
  },
  primaryButton: {
    backgroundColor: '#C9621D',
    borderRadius: 24,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 18,
    paddingHorizontal: 36,
    marginBottom: 24,
    alignSelf: 'flex-start',
  },
  rightPanel: {
    width: '38%',
    backgroundColor: '#1B1A17',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 60,
  },
  bigLogoWrap: {
    width: 120,
    height: 120,
    backgroundColor: '#C9621D',
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 36,
  },
  bigLogoText: {
    color: '#fff',
    fontSize: 48,
    fontWeight: '800',
    fontFamily: Platform.OS === 'web' ? 'Outfit, sans-serif' : 'System',
  },
  rightTagline: {
    color: '#FBF7F0',
    fontSize: 26,
    lineHeight: 38,
    fontFamily: Platform.OS === 'web' ? '"Playfair Display", serif' : 'serif',
    textAlign: 'center',
    opacity: 0.85,
  },
});

const mobile = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FBF7F0',
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: Platform.OS === 'ios' ? 20 : 40,
    justifyContent: 'space-between',
  },
  mainBody: {
    flex: 1,
    justifyContent: 'center',
    marginTop: -40,
  },
  headline: {
    fontSize: 42,
    lineHeight: 48,
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? '"Playfair Display", serif' : 'serif',
    marginBottom: 24,
    letterSpacing: -1,
  },
  subheadline: {
    fontSize: 16,
    lineHeight: 24,
    color: '#4b5563',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
    maxWidth: '85%',
  },
  footer: {
    width: '100%',
  },
  primaryButton: {
    backgroundColor: '#C9621D',
    borderRadius: 24,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
    marginBottom: 24,
  },
});
