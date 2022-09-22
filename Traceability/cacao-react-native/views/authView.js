import React, { useState, useEffect } from 'react';

import { 
    StyleSheet, 
    View,
    Dimensions,
    Text
} from 'react-native';

import { TouchableHighlight } from 'react-native-gesture-handler';
import { VStack, HStack, Spacer } from 'react-native-stacks';

let {height, width} = Dimensions.get('window')

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: 'center',
        flexDirection: 'column',
        alignItems: 'center',
    //   height: height,
    //   width: width,
    },
    header: {
        fontSize: 40,
        fontWeight: 'bold',
        color: '#59CB07'
    },
    subheader: {
        fontSize: 20,
        color: '#d1d1d1',
        fontWeight: 'bold',
        marginTop: 10,
    },
    buttonContainer: {
        // width: width,
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        maxHeight: 75
    },
    driver: {
        paddingTop: 20,
        paddingBottom: 20,
        borderRadius: 10,
        borderWidth: 3,
        borderColor: '#65bd00',
        flex: 1,
        minWidth: "35%",
        justifyContent: 'center',
        backgroundColor: '#59CB07'
        // width: '100%'
    },
    driverText: {
        color: '#fff',
        fontWeight: 'bold',
        textAlign: 'center',
    },
    other: {
        paddingTop: 20,
        paddingBottom: 20,
        borderRadius: 10,
        borderWidth: 3,
        borderColor: '#E4E5E5',
        flex: 1,
        minWidth: "35%",
        justifyContent: 'center'
        // width: '100%'
    },
    otherText: {
        color: '#57CB0D',
        textAlign: 'center',
        fontWeight: 'bold',
    },
    middleSpacer: {
        height: 50
    }
  });

const AuthView = ({ route, navigation }) => {
    const { isDarkMode, backgroundStyle, setAuthStatus } = route.params;

    return (
        <VStack style={styles.container}>
            <Spacer/>
            <Text style={styles.header}>Welcome</Text>
            <Text style={styles.subheader}>Who are you?</Text>
            <View style={styles.middleSpacer}/>
            <HStack style={styles.buttonContainer} spacing={20}>
                <TouchableHighlight
                    style={styles.driver}
                    onPress={() => {setAuthStatus(true)}}
                    underlayColor='#fff'>
                    <Text style={styles.driverText}>Driver</Text>
                </TouchableHighlight>
                <TouchableHighlight
                    style={styles.other}
                    onPress={() => {
                        alert(`Sorry! Only drivers are supported at this time.`);
                    }}
                    underlayColor='#fff'>
                    <Text style={styles.otherText}>Other</Text>
                </TouchableHighlight>
            </HStack>
            <Spacer/>
        </VStack>
    );
}

export default AuthView;