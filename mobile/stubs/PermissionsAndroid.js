/**
 * Web stub for PermissionsAndroid.
 * MapLibre's requestAndroidLocationPermissions.js imports PermissionsAndroid
 * from react-native, but react-native-web does not export it.
 * This stub safely no-ops all permission calls on web.
 */
const PermissionsAndroid = {
  PERMISSIONS: {
    ACCESS_FINE_LOCATION: 'android.permission.ACCESS_FINE_LOCATION',
    ACCESS_COARSE_LOCATION: 'android.permission.ACCESS_COARSE_LOCATION',
  },
  RESULTS: {
    GRANTED: 'granted',
    DENIED: 'denied',
    NEVER_ASK_AGAIN: 'never_ask_again',
  },
  request: async () => 'granted',
  requestMultiple: async () => ({}),
  check: async () => true,
};

// Support both ESM default import and CommonJS require()
module.exports = PermissionsAndroid;
module.exports.default = PermissionsAndroid;
