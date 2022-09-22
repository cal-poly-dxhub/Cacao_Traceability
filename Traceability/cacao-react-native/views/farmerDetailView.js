import React, { useState, useEffect } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { 
  FlatList,
  StyleSheet, 
  Image,
  Text, 
  View,
  StatusBar,
  ScrollView,
  TouchableOpacity
} from 'react-native';
import { TouchableHighlight } from 'react-native-gesture-handler';
import DialogInput from 'react-native-dialog-input';

import NetInfo from "@react-native-community/netinfo";
import AsyncStorage from '@react-native-async-storage/async-storage';

import { 
  Alert,
  SafeAreaView 
} from 'react-native';

import GetLocation from 'react-native-get-location'

import { readNdef, writeNdef } from '../managers/nfcManagerWrapper'
import {set} from "react-native/Libraries/Settings/Settings.ios";
import { postTransaction } from '../managers/apiManager';

const styles = StyleSheet.create({
  sectionContainer: {
    marginTop: 32,
    paddingHorizontal: 24,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: '600',
  },
  sectionDescription: {
    marginTop: 8,
    fontSize: 18,
    fontWeight: '400',
  },
  highlight: {
    fontWeight: '700',
  },
  button: {
    color: 'gray',
    fontWeight: '700',
    fontSize: 35,
    paddingTop: 20,
  },
  boxGif: {
    flex: 1,
    resizeMode: 'contain',
    aspectRatio: 1,
    maxWidth: '80%'
  },
  boxDescription: {
    color: 'darkgrey',
    fontSize: 18,
    paddingTop: 40,
    paddingLeft: 20,
    paddingRight: 20,
  },
  boxNumber: {
    color: 'gray',
    fontSize: 18,
  }
});

const FarmerDetailView = ({ route, navigation }) => {
  const { isDarkMode, backgroundStyle, farmerDetails } = route.params;

  const [currentTransaction, setCurrentTransaction] = useState({});
  const [isDialogVisible, showDialog] = useState(false);
  const [transactionsToPush, pushTransactions] = useState([]);

  let STORAGE_KEY = '@transactions'

  const clearStorage = async () => {
    try {
      await AsyncStorage.clear();
      console.log('Storage successfully cleared!');
    } catch (e) {
      console.warn('Failed to clear the async storage.');
    }
  };

  const savePendingTransactions = async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(transactionsToPush));
      console.log(`${transactionsToPush.length} pending transactions successfully saved! `);
    } catch (e) {
      console.warn('Failed to save pending transactions to the storage!')
    }
  }

  useFocusEffect(
    React.useCallback(() => {
      console.log("switched to farmer details view");

      clearStorage();

      const fetchPendingTransactions = async () => {
        try {
          const value = await AsyncStorage.getItem(STORAGE_KEY);
  
          if (value !== null) {
            pushTransactions(JSON.parse(value));
            console.log(`Successfully fetched ${JSON.parse(value).length} pending transactions!`)
          }
        } catch (e) {
          alert('Failed to fetch pending transactions!')
        }
      }
  
      fetchPendingTransactions()
        .catch(console.error)  
    }, [navigation])
  );

  useEffect(() => {
    savePendingTransactions();
  }, [transactionsToPush]);

  useEffect(() => {
    navigation.setOptions({ title: farmerDetails.name })
  }, [farmerDetails]);

  NetInfo.addEventListener(networkState => {
    console.log("Is connected? - ", networkState.isConnected);

    console.log("number of remaining transactions: ", transactionsToPush.length);

    if (networkState.isConnected && transactionsToPush.length > 0) {
      setTimeout(() => {
        console.log("Attempting to push offline transactions...")

        const pushPendingTransaction = async () => {
          let nextAttemptIndex = 0;

          transactionsToPush.every((transaction, index) => {
            const currentTimestampToRemove = transactionsToPush[index].time_stamp;
    
            postTransaction(transactionsToPush[index]).then((res) => {
              nextAttemptIndex = index + 1;
            }).catch(err => {
              nextAttemptIndex = index;
              return false;
            }).finally(() => {
              pushTransactions(oldTransactions => oldTransactions.slice(nextAttemptIndex, oldTransactions.length));
            })
          });
        }

        pushPendingTransaction();
    }, 5000);
    }
  });

  return (
    <SafeAreaView style={{
      flexGrow: 1,
      marginVertical: 100
    }}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      <DialogInput 
        isDialogVisible={isDialogVisible}
        title={"DialogInput 1"}
        message={"Message for DialogInput #1"}
        hintInput ={"HINT INPUT"}
        submitInput={ (inputText) => {
          writeNdef(inputText).then((resp) => {
            setCurrentTransaction({});
          }).catch(err => {
            console.warn(err);
          }).finally(() => {
            showDialog(false);
          });
          
        }}
        closeDialog={ () => {
          showDialog(false);
        }}>
      </DialogInput>

      <ScrollView
        contentInsetAdjustmentBehavior="automatic"
        style={backgroundStyle}>
        <View
          style={{ flex: 1, flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}
        >
            {!(Object.keys(currentTransaction).length === 0) && (
              <Text style={styles.boxDescription}>
                <Text>
                  You are currently working with batch #
                </Text>
                <Text style={styles.boxNumber}>
                  {currentTransaction.source}
                </Text>            
              </Text>
            )}

            {(Object.keys(currentTransaction).length === 0) && ( // no from-box scanned yet
              <ScrollView>
                <TouchableOpacity onPress={() => {
                  readNdef()
                  .then(bucketId => {
                    const newCurrentTransaction = {...currentTransaction, source : bucketId,farmerDetails : farmerDetails};
                    setCurrentTransaction(newCurrentTransaction);
                    console.log("current transaction after intial scan: ", currentTransaction);
                  }).catch(err => {
                    console.warn(err);
                  });
                }}>
                  <Text style={styles.button}>Scan a Pickup</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => {
                  showDialog(true)
                }}>
                  <Text style={styles.button}>Add New Box</Text>
                </TouchableOpacity>
              </ScrollView>
            )}

            {!(Object.keys(currentTransaction).length === 0) && ( // no to-box scanned yet
              <ScrollView>
                <TouchableOpacity onPress={() => {
                  setCurrentTransaction({});
                }}>
                  <Text style={styles.button}>Mark as Waste</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => {
                    readNdef()
                    .then(bucketId => {
                      const askUser = async () => new Promise((resolve) => {
                        Alert.alert(
                          'Quick Question!',
                          `Is this the last bucket going into ${bucketId}?`,
                          [
                            {text: 'Yes', onPress: () => {
                              currentTransaction.last_dump = true;
                              const newCurrentTransaction = {...currentTransaction, last_dump: true};
                              setCurrentTransaction(newCurrentTransaction);

                              Alert.alert(
                                'One Last Question!',
                                `Is this a final shipment?`,
                                [
                                  {text: 'Yes', onPress: () => {
                                    currentTransaction.final_shipment = true;
                                    const newCurrentTransaction = {...currentTransaction, final_shipment: true};
                                    setCurrentTransaction(newCurrentTransaction);

                                    resolve();
                                  }},
                                  {text: 'No', onPress: () => {
                                    currentTransaction.final_shipment = false;
                                    const newCurrentTransaction = {...currentTransaction, final_shipment: false};
                                    setCurrentTransaction(newCurrentTransaction);

                                    resolve();
                                  }, style: 'cancel'},
                                ],
                                { 
                                  cancelable: true 
                                }
                              ); 
                            }},
                            {text: 'No', onPress: () => {
                              currentTransaction.last_dump = false;
                              currentTransaction.final_shipment = false;
                              const newCurrentTransaction = {...currentTransaction, last_dump: false, final_shipment: false};
                              setCurrentTransaction(newCurrentTransaction);

                              resolve();
                            }, style: 'cancel'},
                          ],
                          { 
                            cancelable: true 
                          }
                        );  
                      });

                      askUser().then(() => {
                        currentTransaction.dest = bucketId;
                        currentTransaction.time_stamp = new Date().toISOString();
                        const newCurrentTransaction = {...currentTransaction, dest : bucketId, time_stamp : new Date().toISOString()};
                        setCurrentTransaction(newCurrentTransaction);
  
                        GetLocation.getCurrentPosition({
                          enableHighAccuracy: true,
                          timeout: 15000,
                        })
                        .then(location => {
                          currentTransaction.location = location;
                          const newCurrentTransaction = {...currentTransaction, location : location};
                          setCurrentTransaction(newCurrentTransaction);
                          console.log("current transaction after last scan: ", currentTransaction);
                        })
                        .catch(error => {
                            const { code, message } = error;
                            console.warn(code, message);
                        }).finally(() => {
                          setTimeout(() => {
                            postTransaction(currentTransaction).then((res) => {
                              alert(`SUCCESS. You moved beans from ${currentTransaction.source} to ${currentTransaction.dest}.`);
                            }).catch(err => {
                              pushTransactions(oldTransactions => [...oldTransactions, currentTransaction]);
    
                              alert("Transaction saved to cache due to network failure!");
                              console.warn(err);
                            }).finally(() => {
                              setCurrentTransaction({});
                            });  
                          }, 1000);
                        });  
                      });  
                    }).catch(err => {
                      console.warn(err);
                      setCurrentTransaction({});
                    });
                }}>
                  <Text style={styles.button}>Scan the Dropoff</Text>
                </TouchableOpacity>
              </ScrollView>
            )}

          <Image
            style={styles.boxGif}
            source={require('../resources/box.gif')}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

export default FarmerDetailView;