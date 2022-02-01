const stream = require('stream');
const AWS = require('aws-sdk');

const fs = require('fs');
const ytdl = require('ytdl-core');

const bucket = process.env.BUCKET_NAME;
const table_name = process.env.TABLE_NAME;

var docClient = new AWS.DynamoDB.DocumentClient();


const downloadYoutube = async(youtubeUrl, key, quality) => {
    return new Promise((resolve, reject) => {
      const passthrough = new stream.PassThrough();

      ytdl(youtubeUrl, { quality })
        .pipe(passthrough);

      const upload = new AWS.S3.ManagedUpload({
        params: {
          Bucket: bucket,
          Key: key,
          Body: passthrough
        },
        partSize: 1024 * 1024 * 64 // 64 MB in bytes
      });
      upload.send((err) => {
        if (err) {
          console.log('error', err);
          reject(err);
        } else {
          console.log('done');

         resolve( {
            "quality": quality,
            "key": key
          });
        }
      });
    });
};



exports.handler = async (event) => {

  console.log(event);

  const info = await ytdl.getInfo(event.youtubeUrl);
  const title = info.videoDetails.title;
  const name = title.replace(/[^a-zA-Z0-9]+/g, "-");
  const publishDate = info.videoDetails.publishDate;
  const id = info.videoDetails.videoId;
  const description = info.videoDetails.description;
  const lengthSeconds = info.videoDetails.lengthSeconds;


  // Example to ensure the format is available
  // itag formats:  251 - audio only,  137 - video only 1920x1080, 22 - audio & video 720p, 136 - video only 1280 x 720
  // Supported Resolutions:  Maximum resolution: 1280x720 - https://developer.amazon.com/en-US/docs/alexa/custom-skills/videoapp-interface-reference.html#supported-video-formats-and-resolutions
  // let format = ytdl.chooseFormat(info.formats, { quality: '137' });

  const key = `unprocessed/${name}.mp4`;
  const audioKey = `unprocessed/${name}-audio.mp4`;

  var params = {
      TableName: table_name,
      Item: {
          "id":  id,
          "title": title,
          "name": name,
          "key": key,
          "publishDate": publishDate,
          "description": description,
          "lengthSeconds": lengthSeconds,
          "youtubeUrl": event.youtubeUrl
      }
  };

  return docClient.put(params).promise()
    .then(() => {
      return Promise.all([
        downloadYoutube(event.youtubeUrl, key, '136'),
        downloadYoutube(event.youtubeUrl, audioKey, '251')
      ]);
    })
    .then((results) => {
      console.log(results);
      return {
        "mediaS3Location": {
          "bucket": bucket,
          "videoKey": results[0].key,
          "audioKey": results[1].key
        }
      };
    })
    .catch((error) => {
      console.error(error);
      return {};
    });
};
