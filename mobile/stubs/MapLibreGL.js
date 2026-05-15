import React from 'react';
import { View, Text } from 'react-native';

const MockView = ({ children, style }) => (
  <View style={[{ backgroundColor: '#e2e8f0', alignItems: 'center', justifyContent: 'center' }, style]}>
    <Text style={{ color: '#64748b', fontWeight: 'bold' }}>Map Placeholder (Native Only)</Text>
    {children}
  </View>
);

const MapLibreGL = {
  MapView: MockView,
  Camera: () => null,
  PointAnnotation: () => null,
  ShapeSource: () => null,
  FillLayer: () => null,
  setAccessToken: () => {},
};

export default MapLibreGL;
