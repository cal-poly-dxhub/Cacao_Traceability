/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 * flow strict-local
 */

import React, {useState} from 'react';
import type {Node} from 'react';
import { 
  PlatformColor,
  useColorScheme 
} from 'react-native';

import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Ionicons from 'react-native-vector-icons/Ionicons';

import FarmersListView from './views/farmersListView';
import FarmerDetailView from './views/farmerDetailView';
import FarmerProfileView from './views/farmerProfileView';
import ScanMapView from './views/scanMapView'
import AuthView from './views/authView';
import ScheduleView from './views/scheduleView';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

const App: () => Node = () => {
  const [selectedFarmer, selectFarmer] = useState(null);

  const [isAuthed, setAuthStatus] = useState(false);

  const isDarkMode = useColorScheme() === 'dark';

  const backgroundStyle = {
    // backgroundColor: 'white'
    backgroundColor: isDarkMode ? PlatformColor('systemGray6') : PlatformColor('systemGray6'),
  };

  const TabBar = () => (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'Schedule') {
            iconName = focused ? 'calendar' : 'calendar-outline';
          } else if (route.name === 'Farmers') {
            iconName = focused ? 'people' : 'people-outline';
          } else if (route.name === 'Map') {
            iconName = focused ? 'map' : 'map-outline';
          }

          // You can return any component that you like here!
          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: 'tomato',
        tabBarInactiveTintColor: 'gray',
      })}
    >
      <Tab.Screen
        name="Schedule"
        component={ScheduleView}
        
      />
      <Tab.Screen
        name="Farmers"
        component={FarmersListView}
      />
      <Tab.Screen
        name="Map"
        component={ScanMapView}
      />
    </Tab.Navigator>
  )

  return (
    <NavigationContainer>
      <Stack.Navigator>
        {isAuthed ? 
        <Stack.Screen 
          name="FarmersListView" 
          component={TabBar} 
          options={{ 
            title: 'Select a Farmer',
          }} 
          options={{headerShown: false}}
        /> :
        <Stack.Screen 
          name="AuthView" 
          component={AuthView} 
          initialParams={{
            isDarkMode: isDarkMode,
            backgroundStyle: backgroundStyle,
            setAuthStatus: setAuthStatus
          }}
          options={{headerShown: false}}
        />
        }
        <Stack.Screen 
          name="FarmerDetailView" 
          component={FarmerDetailView} 
          initialParams={{
            isDarkMode: isDarkMode,
            backgroundStyle: backgroundStyle,
            farmerDetails: selectedFarmer
          }}
          options={{headerShown: false}}
        />
        <Stack.Screen 
          name="FarmerProfile" 
          component={FarmerProfileView} 
          initialParams={{
            isDarkMode: isDarkMode,
            backgroundStyle: backgroundStyle,
            farmerDetails: {}
          }}
          options={{headerShown: false}}
        />
      </Stack.Navigator>
    </NavigationContainer>
 );
};

export default App;
