import React from 'react';
import { 
  FlatList, 
  StyleSheet, 
  Text, 
  View, 
  Image 
} from 'react-native';
import { TouchableHighlight } from 'react-native-gesture-handler';
import farmersJson from '../pseudoData/farmers.json'

const styles = StyleSheet.create({
  container: {
   flex: 1,
   paddingTop: 22
  },
  item: {
    padding: 10,
    fontSize: 18,
    height: 44,
  },
  tinyLogo: {
    width: 50,
    height: 50,
  }
});

const FarmersListView = ({ navigation }) => {
  return (
    <View style={styles.container}>
      <FlatList
        data={farmersJson}
        renderItem={({item}) => (
            <TouchableHighlight
                onPress={() => {
                  navigation.navigate('FarmerProfile', {
                    farmerDetails: item
                  });
                }}
            >
                <View style={{flexDirection:'row', alignItems:'center', justifyContent:'flex-start'}}>
                    <Image 
                      style={styles.tinyLogo}
                      source={{uri: item.imageUrl}}
                    />
                    <Text style={styles.item}>
                        {item.name}
                    </Text>
                </View>
            </TouchableHighlight>

        )}
      />
    </View>
  );
}

export default FarmersListView;