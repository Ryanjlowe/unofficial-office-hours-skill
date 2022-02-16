const stream = require('stream');
const AWS = require('aws-sdk');

const ytdl = require('ytdl-core');

const table_name = process.env.TABLE_NAME;

var docClient = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {

  console.log(event);

  const info = await ytdl.getInfo(event.youtubeUrl);
  const title = info.videoDetails.title;
  const name = title.replace(/[^a-zA-Z0-9]+/g, "-");
  const publishDate = info.videoDetails.publishDate;
  const id = info.videoDetails.videoId;
  const description = info.videoDetails.description;

  console.log(JSON.stringify(info));

  var params = {
      TableName: table_name,
      Item: {
          "id":  id,
          "title": title,
          "name": name,
          "publishDate": publishDate,
          "description": description,
          "youtubeUrl": event.youtubeUrl
      }
  };

  return docClient.put(params).promise()
    .then(() => {
      return {
        "youtubeUrl": event.youtubeUrl,
        "youtubeStatus": info.player_response.playabilityStatus.status,
        "metadata":{
          "YouTubeVideoID": id,
          "Title": title,
          "Name": name,
          "PublishDate": publishDate,
          "YouTubeURL": event.youtubeUrl
        }
      };
    })
    .catch((error) => {
      console.error(error);
      return {};
    });
};
