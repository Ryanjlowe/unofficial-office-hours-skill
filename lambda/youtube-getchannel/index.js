const AWS = require('aws-sdk');

const ytpl = require('ytpl');

const CHANNEL_ID = process.env.CHANNEL_ID;

exports.handler = async (event) => {

  console.log(event);

  let total = 0;
  let urls = [];
  
  let playlist = await ytpl(CHANNEL_ID, { pages: 1 });
  total += playlist.items.length;
  while (playlist.continuation != null) {
    
    playlist = await ytpl.continueReq(playlist.continuation);
    
    total += playlist.items.length;

    urls = urls.concat(playlist.items.map((item) => item.shortUrl));
    
  }
  console.log("Total Found: " + total);
  console.log(urls);
  
  return {
    "Urls": urls,
    "Index": 0,
    "Length": total
  };
  
  
};
