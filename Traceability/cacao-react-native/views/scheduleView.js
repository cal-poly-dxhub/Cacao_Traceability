import React, { useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';

import scheduleJson from '../pseudoData/schedule.json'
import farmersJson from '../pseudoData/farmers.json'

import { 
    StyleSheet, 
    View,
    Dimensions,
    Text
} from 'react-native';

import { TouchableHighlight } from 'react-native-gesture-handler';
import { VStack, HStack, Spacer } from 'react-native-stacks';
import SectionList from 'react-native/Libraries/Lists/SectionList';

const styles = StyleSheet.create({
    headerRow: {
        backgroundColor: '#F2F2F2'
    },
    header: {
        fontWeight: 'bold',
        fontSize: 20,
        color: '#4B4B4B',
        margin: 10,
    },
    apptRow: {
        // margin: 10,
        // marginLeft: 15,
        // marginRight: 15,
        paddingTop: 20,
        paddingBottom: 20,
        borderRadius: 10,
        borderWidth: 3,
        borderColor: '#E4E5E5',
        flex: 1,
        minWidth: "35%",
        justifyContent: 'center',
        backgroundColor: 'white'
        // width: '100%'
    },
    timestamp: {
        fontWeight: '900',
        color: '#4B4A4C'
    },
    apptType: {
        fontWeight: 'bold',
        color: '#59CB07'
    },
    farmerName: {
        fontWeight: 'bold',
        color: '#A2A0A4'
    }
  });

const ScheduleView = ({ navigation }) => {
    const [sortedAppointmentsList, setSortedAppointmentsList] = useState([]);
    
    useFocusEffect(
        React.useCallback(() => {          
            sortAppointments(scheduleJson);
        }, [navigation])
    );

    const sortAppointments = (appointments) => {
        let sortedAppointments = []

        for (const appointment of appointments) {
            const fullDate = new Date(appointment.visitDate);
            const generalDate = `${fullDate.getFullYear()}_${fullDate.getMonth()}_${fullDate.getDay()}`;

            const indexToInsertInto = sortedAppointments.findIndex(apptIter => apptIter.title === generalDate);

            if (indexToInsertInto == -1) {
                sortedAppointments.push({
                    title: generalDate,
                    data: [appointment]
                });
            } else {
                sortedAppointments[indexToInsertInto].data.push(appointment);
            }
        }

        setSortedAppointmentsList(sortedAppointments);
    }

    const Item = ({ appt }) => {
        const farmerDetails = farmersJson.find(farmer => farmer.id == appt.farmerId)
        const dateObj = new Date(appt.visitDate);

        return (
            <TouchableHighlight 
                underlayColor="gray"
                style={{
                    borderRadius: 10,
                    margin: 10,
                    marginLeft: 15,
                    marginRight: 15,
                }}
                onPress={() => {
                    navigation.navigate('FarmerDetailView', { farmerDetails: farmerDetails })
            }}>
                <HStack 
                    style={styles.apptRow} 
                    spacing={10}
                >
                    <Text style={styles.timestamp}>{dateObj.getHours() + ":" + dateObj.getMinutes()}</Text>
                    <Spacer/>
                    <VStack alignment='trailing'>
                        <Text style={styles.apptType}>{appt.visitPurpose.toUpperCase()}</Text>
                        <Text style={styles.farmerName}>{farmerDetails.name}</Text>
                    </VStack>
                </HStack>
            </TouchableHighlight>
        );
    };

    const Header = ({ title }) => {
        return (
            <HStack style={styles.headerRow}>
                <Text style={styles.header}>{title}</Text>
                <Spacer/>
            </HStack>
        );
    };

    return (
        <SectionList
            sections={sortedAppointmentsList}
            keyExtractor={(appt, index) => appt.idScheduleVisit}
            renderItem={({item}) => <Item appt={item} />}
            renderSectionHeader={({ section: { title } }) => <Header title={title} />}
        />
    );
}

export default ScheduleView;