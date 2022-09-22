import axios from 'axios';

const baseUrl = 'https://xps6mstzpa.execute-api.us-west-2.amazonaws.com/dev';

const employeeId = '83c1e87a-96bf-4378-9e75-7296dfb89412'

export async function postTransaction(transactionDetails) {
    const farmerId = transactionDetails.farmerDetails.hasOwnProperty("id") ? transactionDetails.farmerDetails.id : null;
    const location = transactionDetails.location;
    const source = transactionDetails.source;
    const dest = transactionDetails.dest;
    const last_dump = transactionDetails.last_dump;
    const final_shipment = transactionDetails.final_shipment;
    const source_weight_kg = 0;
    const time_stamp = transactionDetails.time_stamp

    console.log("did i get read? ", last_dump)
    
    console.log(`sending: ${[
        employeeId,
        farmerId,
        location,
        source,
        dest,
        last_dump,
        final_shipment,
        source_weight_kg,
        time_stamp
    ]}`);

    return axios.post(`${baseUrl}/transactions`, null, {
        params: {
            employeeId,
            farmerId,
            location,
            source,
            dest,
            last_dump,
            final_shipment,
            source_weight_kg,
            time_stamp
        }
    }).then((resp) => {
        if (resp.status === 200) {
            return true;
        } else {
            throw "Did not get a 200 response!"
        }  
    }).catch(err => {
        throw "failed to POST transaction!"
    });
}
export async function getAllTransactions() {
    const data = await axios.get(`${baseUrl}/transactions`, {
        params: {
            employeeId
        }
    }).then(resp => {
        console.log("resp: ", resp.data)
        return resp.data
    }).catch(err => {
        console.log(err)
    });

    return data
}