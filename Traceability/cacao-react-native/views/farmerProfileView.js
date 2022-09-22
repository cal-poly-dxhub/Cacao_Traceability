import React, { useState } from 'react';

import { useFocusEffect } from '@react-navigation/native';

import { 
  FlatList, 
  StyleSheet, 
  Text, 
  View, 
  Image 
} from 'react-native';

import { TouchableHighlight } from 'react-native-gesture-handler';

import { VStack, HStack, Spacer } from 'react-native-stacks';
import { SafeAreaView } from 'react-native-safe-area-context';

const styles = StyleSheet.create({
    container: {
     flex: 1,
    },
    name: {
        fontWeight: '900',
        fontSize: 30,
    },
    portrait: {
        width: 200,
        height: 200,
        borderRadius: 100
    },
    phone: {
        color: 'gray',
        fontWeight: 'bold',
        fontSize: 20
    }
  });  

const FarmerProfileView = ({ route, navigation }) => {
    const { isDarkMode, backgroundStyle, farmerDetails } = route.params;
    const [currentFarmer, changeCurrentFarmer] = useState(null);

    useFocusEffect(
        React.useCallback(() => {    
            changeCurrentFarmer(farmerDetails);
        }, [navigation])
    );

    if (currentFarmer != null) {
        return (
            <SafeAreaView style={styles.container}>
                <VStack>
                    <Image 
                        style={styles.portrait}
                        source={{uri: currentFarmer.imageUrl}}
                    />
                    <View style={{height: 20}}/>
                    <Text style={styles.name}>{currentFarmer.name}</Text>
                    <Text style={styles.phone}>{currentFarmer.phone}</Text>
                </VStack>
            </SafeAreaView>
        );    
    } else {
        return <View/>
    }
}

export default FarmerProfileView;