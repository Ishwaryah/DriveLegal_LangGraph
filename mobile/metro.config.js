const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

if (!config.resolver) {
  config.resolver = {};
}

// ---------------------------------------------------------------------------
// Resolve platform-specific extensions: .web.tsx > .tsx etc.
// ---------------------------------------------------------------------------
config.resolver.sourceExts = [
  'web.tsx',
  'web.ts',
  'web.jsx',
  'web.js',
  ...(config.resolver.sourceExts || []),
];

// ---------------------------------------------------------------------------
// Custom resolver: block native-only MapLibre modules on web.
//
// When Metro bundles for web it aliases `react-native` → `react-native-web`.
// react-native-web does NOT export PermissionsAndroid, so any MapLibre file
// that imports it (e.g. requestAndroidLocationPermissions.js) must be
// redirected to a safe no-op stub.
//
// `resolveRequest` is the only hook that sees the *resolved* path and can
// redirect it before Metro emits the "Unable to resolve" error.
// ---------------------------------------------------------------------------
const permissionsStub = path.resolve(
  __dirname,
  'stubs/PermissionsAndroid.js'
);

const requestAndroidStub = path.resolve(
  __dirname,
  'stubs/requestAndroidLocationPermissions.js'
);

const mapLibreStub = path.resolve(
  __dirname,
  'stubs/MapLibreGL.js'
);

config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (platform === 'web') {
    // Redirect the PermissionsAndroid path that react-native-web is missing.
    if (
      moduleName === 'react-native-web/dist/exports/PermissionsAndroid' ||
      moduleName.endsWith('/PermissionsAndroid')
    ) {
      return { filePath: permissionsStub, type: 'sourceFile' };
    }

    // Redirect the entire requestAndroidLocationPermissions module
    if (moduleName.includes('requestAndroidLocationPermissions')) {
      return { filePath: requestAndroidStub, type: 'sourceFile' };
    }

    // Redirect MapLibre itself on web
    if (moduleName === '@maplibre/maplibre-react-native') {
      return { filePath: mapLibreStub, type: 'sourceFile' };
    }

    // Handle node: prefixed modules (Node 20+) to avoid mkdir errors on Windows
    if (moduleName.startsWith('node:')) {
      return { type: 'empty' };
    }
  }

  // Fall through to default resolution for everything else.
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
