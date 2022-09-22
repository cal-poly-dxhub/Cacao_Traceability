import React, { useState } from 'react';
import MapView from 'react-native-maps';
import { Marker } from 'react-native-maps';
import { useFocusEffect } from '@react-navigation/native';

import { getAllTransactions } from '../managers/apiManager';

import { 
  StyleSheet, 
  View,
  Dimensions
} from 'react-native';

let {height, width} = Dimensions.get('window')

const styles = StyleSheet.create({
  container: {
    height: height,
    width: width,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  }
});

const ScanMapView = ({ navigation }) => {
  const [transactions, setTransactions] = useState([]);

  useFocusEffect(
    React.useCallback(() => {
      console.log("viewing of map");

      const fetchTransactions = async () => {
        const transactionsFetch = await getAllTransactions()
        console.log(transactions)
        setTransactions(transactionsFetch);
      }
  
      fetchTransactions();
    }, [navigation])
  );

  const markers = useState([])
    return (
      <View style={styles.container}>
        {transactions.length > 0 ? (
          <MapView
            style={styles.map}
            initialRegion={{
              latitude: transactions[0].gps.latitude,
              longitude: transactions[0].gps.longitude,
              latitudeDelta: 0.0922,
              longitudeDelta: 0.0421,
            }}
          >
            {transactions.map((transaction, index) => (
              <Marker
                key={index}
                coordinate={{
                  latitude : transaction.gps.latitude, 
                  longitude : transaction.gps.longitude 
                }}
              />
            ))}
          </MapView>
        ) : 
          <View/>
        }
      </View>
    );
  }
  
  export default ScanMapView;