const stream = require('stream');
const AWS = require('aws-sdk');

const ytdl = require('ytdl-core');

const bucket = process.env.BUCKET_NAME;


const downloadYoutube = async(youtubeUrl, key, quality) => {
  const passthrough = new stream.PassThrough();

  console.log(youtubeUrl);
  console.log(key);
  console.log(quality);

  ytdl(youtubeUrl, { quality })
    // Uncomment this for debuging - but it logs A LOT over slow connections
    // .on('progress', (_, downloaded, total) => {
    //   console.log(JSON.stringify({downloaded, total }));
    // })
    .pipe(passthrough);

  const upload = new AWS.S3.ManagedUpload({
    params: {
      Bucket: bucket,
      Key: key,
      Body: passthrough
    },
    partSize: 1024 * 1024 * 64 // 64 MB in bytes
  });
  upload.on('httpUploadProgress', (event) => {
    console.log(event.loaded * 100 / event.total);
  });
  return upload.promise()
    .then((data) => {
      console.log(`${quality} done`);
      return {
        "quality": quality,
        "key": key
      };
    })
    .catch((err) => {
      console.log('error', err);
      return err;
    });
};



exports.handler = async (event) => {

  console.log(event);

  const info = await ytdl.getInfo(event.youtubeUrl);

  const title = info.videoDetails.title;
  const name = title.replace(/[^a-zA-Z0-9]+/g, "-");

  console.log(JSON.stringify(info));

  // Example to ensure the format is available
  // itag formats:  251 - audio only,  137 - video only 1920x1080, 22 - audio & video 720p, 136 - video only 1280 x 720
  // Supported Resolutions:  Maximum resolution: 1280x720 - https://developer.amazon.com/en-US/docs/alexa/custom-skills/videoapp-interface-reference.html#supported-video-formats-and-resolutions
  // let format = ytdl.chooseFormat(info.formats, { quality: '137' });

  const key = `unprocessed/${name}.mp4`;
  const audioKey = `unprocessed/${name}-audio.mp4`;

  console.log("starting download");

  const promises = [];

  try {
    let format = ytdl.chooseFormat(info.formats, { quality: '95' });
    promises.push(downloadYoutube(event.youtubeUrl, key, '95'));

  } catch {

    promises.push(downloadYoutube(event.youtubeUrl, key, '136'));
    promises.push(downloadYoutube(event.youtubeUrl, audioKey, '251'));

  }

  return Promise.all(promises)
    .then((results) => {
      console.log(results);

      let audioKey = '';
      if (results.length > 1) {
        audioKey = results[1].key;
      }

      return {
        "mediaS3Location": {
          "bucket": bucket,
          "videoKey": results[0].key,
          "audioKey": audioKey
        }
      };
    })
    .catch((error) => {
      console.error(error);
      return {};
    });
};
