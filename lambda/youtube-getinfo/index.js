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

  let epochStart = info.player_response.playabilityStatus.status === 'OK' ? 0 :
            parseInt(info.player_response.playabilityStatus.liveStreamability.liveStreamabilityRenderer.offlineSlate.liveStreamOfflineSlateRenderer.scheduledStartTime);

  const now = Math.round(Date.now() / 1000);

  let secondsWait = epochStart === 0 ? 0 : (epochStart - now) + (70 * 60);

  return docClient.put(params).promise()
    .then(() => {
      return {
        "youtubeUrl": event.youtubeUrl,
        "secondsWait": secondsWait,
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
