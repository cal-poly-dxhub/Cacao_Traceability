import NfcManager, {NfcTech, Ndef} from 'react-native-nfc-manager';
import {set} from "react-native/Libraries/Settings/Settings.ios";

NfcManager.start();

export async function readNdef() {  
  try {
    // register for the NFC tag with NDEF in it
    await NfcManager.requestTechnology(NfcTech.MifareIOS);
    // the resolved tag object will contain `ndefMessage` property
    const tag = await NfcManager.getTag();
    
    let cmd = NfcManager.sendMifareCommandIOS;
    
    resp = await cmd([0x3A, 4, 4]);
    let payloadLength = parseInt(resp.toString().split(",")[1]);
    let payloadPages = Math.ceil(payloadLength / 4);
    let startPage = 5;
    let endPage = startPage + payloadPages - 1;
    
    resp = await cmd([0x3A, startPage, endPage]);
    bytes = resp.toString().split(",");
    let text = "";
    
    for(let i=0; i<bytes.length; i++){
      if (i < 5){
        continue;
      }
      
      if (parseInt(bytes[i]) === 254){
        break;
      }
      
      text = text + String.fromCharCode(parseInt(bytes[i]));
    }
    
    if (parseInt(text) != NaN) {
      console.log(`Box #${text} scanned!`);
      NfcManager.cancelTechnologyRequest();
      
      return parseInt(text)
    } else {
      throw "Did not find a number"
    }
  } catch (ex) {
    NfcManager.cancelTechnologyRequest();
    throw ex;
  }
}

export async function writeNdef(text) {
  if (!text){
    Alert.alert("Nothing to write");
    return;
  }
  try {
    let tech = NfcTech.MifareIOS;
    let resp = await NfcManager.requestTechnology(tech, {
      alertMessage: 'Please tap the NFC tag located on the box'
    });
    
    let fullLength = text.length + 7;
    let payloadLength = text.length + 3;
    
    let cmd = Platform.OS === 'ios' ? NfcManager.sendMifareCommandIOS : NfcManager.transceive;
    
    resp = await cmd([0xA2, 0x04, 0x03, fullLength, 0xD1, 0x01]); // 0x0C is the length of the entry with all the fluff (bytes + 7)
    resp = await cmd([0xA2, 0x05, payloadLength, 0x54, 0x02, 0x65]); // 0x54 = T = Text block, 0x08 = length of string in bytes + 3
    
    let currentPage = 6;
    let currentPayload = [0xA2, currentPage, 0x6E];
    
    for(let i=0; i<text.length; i++){
      currentPayload.push(text.charCodeAt(i));
      if (currentPayload.length == 6){
        resp = await cmd(currentPayload);
        currentPage += 1;
        currentPayload = [0xA2, currentPage];
      }
    }
    
    // close the string and fill the current payload
    currentPayload.push(254);
    while(currentPayload.length < 6){
      currentPayload.push(0);
    }
    
    resp = await cmd(currentPayload);
    console.log("wrote data: ", resp.toString());
    NfcManager.cancelTechnologyRequest().catch(() => 0);
    return resp.toString();
  } catch (ex) {
    NfcManager.cancelTechnologyRequest().catch(() => 0);
    return ex;
  }
}