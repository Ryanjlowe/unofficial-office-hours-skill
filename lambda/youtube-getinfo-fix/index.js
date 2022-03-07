const stream = require('stream');
const AWS = require('aws-sdk');

const ytdl = require('ytdl-core');
const { INSPECT_MAX_BYTES } = require('buffer');

const table_name = process.env.TABLE_NAME;

var docClient = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {

  console.log(event);

  const params = {
    TableName: table_name
  };

  const scan = [];
  let items;
  do {
    items = await docClient.scan(params).promise();
    items.Items.forEach((i) => scan.push(i));
    params.ExclusiveStartKey  = items.LastEvaluatedKey;
  } while (typeof items.LastEvaluatedKey !== "undefined");


  console.log(JSON.stringify(scan));

  const filtered = scan.filter(i => i.lengthInSeconds === undefined && i.youtubeUrl !== undefined);
  
  for (var i = 0; i < filtered.length; i++) {
    

    console.log(JSON.stringify(filtered[i]));
    console.log(filtered[i].youtubeUrl);

    const info = await ytdl.getInfo(filtered[i].youtubeUrl);

    const title = info.videoDetails.title;
    const name = title.replace(/[^a-zA-Z0-9]+/g, "-");
    const publishDate = info.videoDetails.publishDate;
    const id = info.videoDetails.videoId;
    const description = info.videoDetails.description;
    const lengthInSeconds = info.videoDetails.lengthSeconds;

    console.log(JSON.stringify(info));

    var param = {
        TableName: table_name,
        Item: {
            "id":  id,
            "title": title,
            "name": name,
            "publishDate": publishDate,
            "description": description,
            "youtubeUrl": filtered[i].youtubeUrl,
            "lengthInSeconds": lengthInSeconds
        }
    };
    await docClient.put(param).promise();
    console.log("WROTE IT");
    

  }
};
