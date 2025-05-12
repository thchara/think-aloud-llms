// Audio analysis scripts thanks to Claude
async function analyzeRecordedAudio(blob, fftSize = 2048, nSeconds = 10) {
  // Previous FFT implementation remains the same...
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const arrayBuffer = await blob.arrayBuffer();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  const channelData = audioBuffer.getChannelData(0);

  // get only the last n seconds
  const startIdx = Math.max(
    0,
    channelData.length - nSeconds * audioBuffer.sampleRate
  );
  const lastSecondsChannelData = channelData.slice(startIdx);

  const sampleRate = audioBuffer.sampleRate;
  const numSegments = Math.floor(lastSecondsChannelData.length / fftSize);
  const results = [];

  for (let i = 0; i < numSegments; i++) {
    const start = i * fftSize;
    const end = start + fftSize;
    const segment = lastSecondsChannelData.slice(start, end);

    const fft = new FFT(segment.length);
    const spectrum = fft.forward(Array.from(segment));

    const magnitudes = new Array(fft.spectrum.length);
    for (let j = 0; j < fft.spectrum.length; j++) {
      magnitudes[j] = Math.sqrt(
        Math.pow(fft.spectrum[j].real, 2) + Math.pow(fft.spectrum[j].imag, 2)
      );
    }

    results.push({
      timeOffset: i * (fftSize / sampleRate),
      frequencyData: magnitudes,
      timeData: Array.from(segment),
    });
  }

  await audioContext.close();

  return {
    results,
    metadata: {
      duration: audioBuffer.duration,
      sampleRate,
      fftSize,
      frequencyBinCount: fftSize / 2,
      frequencyResolution: sampleRate / fftSize,
      totalSegments: numSegments,
      timeStep: fftSize / sampleRate,
    },
  };
}

// FFT implementation
class FFT {
  constructor(size) {
    this.size = size;
    this.spectrum = new Array(size / 2)
      .fill()
      .map(() => ({ real: 0, imag: 0 }));

    // Precompute reverse bits table
    this.reverseBits = new Array(size);
    for (let i = 0; i < size; i++) {
      this.reverseBits[i] = this.reverse(i);
    }
  }

  reverse(num) {
    let result = 0;
    let bits = Math.log2(this.size);
    for (let i = 0; i < bits; i++) {
      result = (result << 1) | (num & 1);
      num >>= 1;
    }
    return result;
  }

  forward(input) {
    const n = this.size;
    const output = new Array(n);

    // Bit reversal
    for (let i = 0; i < n; i++) {
      output[this.reverseBits[i]] = input[i];
    }

    // FFT computation
    for (let size = 2; size <= n; size *= 2) {
      const halfsize = size / 2;
      const step = Math.PI / halfsize;

      for (let i = 0; i < n; i += size) {
        let angle = 0;

        for (let j = i; j < i + halfsize; j++) {
          const cos = Math.cos(angle);
          const sin = Math.sin(angle);

          const tReal = output[j + halfsize] * cos + output[j] * sin;
          const tImag = output[j + halfsize] * sin - output[j] * cos;

          output[j + halfsize] = output[j] - tReal;
          output[j] = output[j] + tReal;

          angle += step;
        }
      }
    }

    // Fill spectrum array
    for (let i = 0; i < n / 2; i++) {
      this.spectrum[i] = {
        real: output[i],
        imag: output[i + n / 2],
      };
    }

    return this.spectrum;
  }
}

function getFrequencyRangeActivity(analysis, minFreq, maxFreq) {
  const { sampleRate, fftSize } = analysis.metadata;
  const binSize = sampleRate / fftSize;

  // Calculate which FFT bins correspond to our frequency range
  const minBin = Math.floor(minFreq / binSize);
  const maxBin = Math.ceil(maxFreq / binSize);

  // Analyze each segment
  const rangeActivity = analysis.results.map((segment) => {
    // Sum up the magnitude of all frequencies in our range
    let totalActivity = 0;
    for (
      let bin = minBin;
      bin <= maxBin && bin < segment.frequencyData.length;
      bin++
    ) {
      totalActivity += segment.frequencyData[bin];
    }

    return {
      timeOffset: segment.timeOffset,
      activity: totalActivity,
      // Also include the average for this range
      averageActivity: totalActivity / (maxBin - minBin + 1),
    };
  });

  // Calculate some statistics for the entire range
  const activities = rangeActivity.map((r) => r.activity);
  const stats = {
    minActivity: Math.min(...activities),
    maxActivity: Math.max(...activities),
    averageActivity: activities.reduce((a, b) => a + b, 0) / activities.length,
    frequencyRange: {
      min: minFreq,
      max: maxFreq,
      binSize,
      minBin,
      maxBin,
    },
  };

  return {
    rangeActivity,
    stats,
  };
}

async function processRecordingWithRanges(
  blob,
  frequencyRanges,
  nSeconds = 10
) {
  try {
    const analysis = await analyzeRecordedAudio(blob, 2048, nSeconds);

    // Analyze each frequency range
    const rangeAnalysis = {};
    for (const [rangeName, range] of Object.entries(frequencyRanges)) {
      rangeAnalysis[rangeName] = getFrequencyRangeActivity(
        analysis,
        range.min,
        range.max
      );
    }

    return rangeAnalysis;
  } catch (error) {
    console.error("Error processing audio:", error);
    throw error;
  }
}

var jsPsychGameOfNAudioRecording = (function (jspsych) {
  "use strict";

  const info = {
    name: "GameOfN-audio-recording",
    parameters: {
      html: {
        type: jspsych.ParameterType.HTML_STRING,
        default: undefined,
      },
      choices: {
        type: jspsych.ParameterType.INT,
        default: undefined,
      },
      target: {
        type: jspsych.ParameterType.INT,
        default: undefined,
      },
      trial_duration: {
        type: jspsych.ParameterType.INT,
        pretty_name: "Trial duration",
        default: null,
      },
      alert_threshold: {
        type: jspsych.ParameterType.INT,
        default: 8,
      },
      voice_check_frequency: {
        type: jspsych.ParameterType.INT,
        default: 20,
      },
    },
  };

  /**
   * **GameOfN**
   *
   *
   * @author Daniel Wurgaft
   */
  class jsPsychGameOfNAudioRecording {
    constructor(jsPsych) {
      this.jsPsych = jsPsych;
      this.recorded_data_chunks = [];
      this.alert_counter = 0;
    }

    trial(display_element, trial) {
      var jspsych = this.jsPsych;

      var response = {
        rt: null,
        timeout: false,
        button_clicks: [],
        correct: 1,
        choices: trial.choices,
        target: trial.target,
        trial_duration: trial.trial_duration,
        alert_threshold: trial.alert_threshold,
        voice_check_frequency: trial.voice_check_frequency,
      };

      var html = trial.html;

      //display buttons
      var buttons = [];
      var button_html = '<button class="jspsych-btn">%choice%</button>';
      for (var i = 0; i < trial.choices.length; i++) {
        buttons.push(button_html);
      }

      for (var i = 0; i < trial.choices.length; i++) {
        var str = buttons[i].replace(/%choice%/g, trial.choices[i]);
        html +=
          '<div class="jspsych-audio-button-response-button" style="cursor: pointer; display: inline-block; margin:' +
          "2px" +
          " " +
          "8px" +
          '" id="jspsych-audio-button-response-button-' +
          i +
          '" data-choice="' +
          trial.choices[i] +
          '">' +
          str +
          "</div>";
      }
      // add a space gap between the choices buttons and operations buttons
      html += "<br><br>";
      var operations = ["x", "/", "+", "-"];
      for (var i = 0; i < operations.length; i++) {
        html +=
          '<div class="jspsych-audio-button-response-button" style="cursor: pointer; display: inline-block; margin:' +
          "2px" +
          " " +
          "8px" +
          '" id="jspsych-audio-button-response-button-' +
          i +
          trial.choices.length +
          '" data-choice="' +
          operations[i] +
          '">' +
          '<button class="jspsych-btn">' +
          operations[i] +
          "</button></div>";
      }
      var brackets = ["(", ")"];
      for (var i = 0; i < 2; i++) {
        html +=
          '<div class="jspsych-audio-button-response-button" style="cursor: pointer; display: inline-block; margin:' +
          "2px" +
          " " +
          "8px" +
          '" id="jspsych-audio-button-response-button-' +
          i +
          trial.choices.length +
          operations.length +
          '" data-choice="' +
          brackets[i] +
          '">' +
          '<button class="jspsych-btn">' +
          brackets[i] +
          "</button></div>";
      }
      html += "<br><br>";
      html +=
        '<div class="jspsych-audio-button-response-button" style="cursor: pointer; display: inline-block; margin:' +
        "2px" +
        " " +
        "8px" +
        '" id="jspsych-audio-button-response-button-' +
        "delete" +
        '" data-choice="' +
        "delete" +
        '">' +
        '<button class="jspsych-btn">Delete</button>' +
        "</div>";
      html += "</div>";

      html +=
        '<input type="text" id="input" value="" name="#jspsych-survey-text-response' +
        '" size="18' +
        '" ' +
        '"style=" position: absolute; top: 5%;" disabled></input>';

      html +=
        '<div class="jspsych-audio-button-response-button" style="cursor: pointer; display: inline-block; margin:' +
        "2px" +
        " " +
        "8px" +
        '" id="jspsych-audio-button-response-button-' +
        "submit" +
        '" data-choice="' +
        "submit" +
        '">' +
        '<button class="jspsych-btn">Submit Answer</button>' +
        "</div>";
      html += "</div>";

      display_element.innerHTML = html;
      // start recording
      this.recorder = this.jsPsych.pluginAPI.getMicrophoneRecorder();
      this.setupRecordingEvents(display_element, trial);
      this.startRecording(trial.voice_check_frequency);
      // start time
      var startTime = performance.now();

      // keep track of the past results of equations
      var pastResults = [""];
      var disabled_buttons = [];

      function button_response(e) {
        var choice = e.currentTarget.getAttribute("data-choice"); // don't use dataset for jsdom compatibility
        if (choice == "submit") {
          response.button_clicks.push({
            button: "submit",
            "time:": performance.now() - startTime,
            value: document.getElementById("input").value,
          });
          // replace x with * in input
          var input = document
            .getElementById("input")
            .value.replaceAll(/x/g, "*");
          // replace Ã· with / in  input
          input = input.replaceAll(/Ã·/g, "/");
          try {
            var result = eval(input);
          } catch (SyntaxError) {
            alert("Invalid equation provided!");
            return;
          }
          // round result to 2 decimal places
          result = Math.round((result + Number.EPSILON) * 100) / 100;
          if (
            result == trial.target &&
            disabled_buttons.length == trial.choices.length
          ) {
            after_correct_response(jspsych);
          } else {
            alert("Incorrect answer or not all numbers used!");
          }
        } else if (choice == "delete") {
          // remove last number or operation from input
          var input = document.getElementById("input").value;
          // check if last character is an operation
          if (operations.concat(brackets).indexOf(input.slice(-1)) != -1) {
            document.getElementById("input").value = input.slice(0, -1);
          }
          // if last character is a number, remove all numbers until an operation is found
          else {
            // find the last number by iterating over the last digits of the input until finding an operation
            var i = input.length - 1;
            while (
              i >= 0 &&
              operations.concat(brackets).indexOf(input.slice(i, i + 1)) == -1
            ) {
              i--;
            }
            // remove last number from input
            document.getElementById("input").value = input.slice(0, i + 1);
            // enable last button disabled
            var btn = disabled_buttons.pop();
            if (btn) {
              btn.querySelector("button").disabled = false;
              btn.addEventListener("click", button_response);
            }
          }
          response.button_clicks.push({
            button: "delete",
            "time:": performance.now() - startTime,
            value: document.getElementById("input").value,
          });
        } else {
          // if choice is a number or operation
          var choice_index = trial.choices.indexOf(parseInt(choice));
          var op_index = operations.concat(brackets).indexOf(choice);
          var lastChar = document.getElementById("input").value.slice(-1);

          // check if choice is a number
          if (choice_index != -1) {
            // if last character is a number, alert user to add an operation
            if (!isNaN(parseInt(lastChar))) {
              alert(
                "Number must be followed by arithmetic operation! (+, -, x, /)"
              );
              // otherwise, add number to input and disable button
            } else {
              document.getElementById("input").value += choice;

              // disable number button pressed
              document
                .getElementById(e.currentTarget.id)
                .removeEventListener("click", button_response);
              document
                .getElementById(e.currentTarget.id)
                .querySelector("button").disabled = true;
              disabled_buttons.push(e.currentTarget);
              response.button_clicks.push({
                button: choice,
                "time:": performance.now() - startTime,
                value: document.getElementById("input").value,
              });
            }
          } else if (op_index != -1) {
            // if last character is an operation, alert user to add a number
            if (
              operations.indexOf(lastChar) != -1 &&
              brackets.indexOf(choice) == -1
            ) {
              alert("Operation must be followed by a number or bracket!");
            }
            // otherwise, add the operation to input
            else {
              document.getElementById("input").value += choice;
              response.button_clicks.push({
                button: choice,
                "time:": performance.now() - startTime,
                value: document.getElementById("input").value,
              });
            }
          }
        }
      }

      function disable_buttons() {
        var btns = document.querySelectorAll(
          ".jspsych-audio-button-response-button"
        );
        for (var i = 0; i < btns.length; i++) {
          var btn_el = btns[i].querySelector("button");
          if (btn_el) {
            btn_el.disabled = true;
          }
          btns[i].removeEventListener("click", button_response);
        }
      }

      function enable_buttons() {
        var btns = document.querySelectorAll(
          ".jspsych-audio-button-response-button"
        );
        for (var i = 0; i < btns.length; i++) {
          var btn_el = btns[i].querySelector("button");
          if (btn_el) {
            btn_el.disabled = false;
          }
          btns[i].addEventListener("click", button_response);
        }
      }

      enable_buttons();

      this.end_trial = (isCorrectResponse) => {
        // measure rt
        var endTime = performance.now();
        var rt = Math.round(endTime - startTime);
        var final_response = document.getElementById("input").value;
        const finishTrial = () => {
          console.log("end trial");

          // stop the recording
          this.stopRecording().then(() => {
            console.log("recording is over");
            this.recorder.removeEventListener(
              "dataavailable",
              this.data_available_handler
            );
            this.recorder.removeEventListener("start", this.start_event_handler);
            this.recorder.removeEventListener("stop", this.stop_event_handler);
            // kill any remaining setTimeout handlers
            this.jsPsych.pluginAPI.clearAllTimeouts();

            response.rt = rt;

            // disable all the buttons after a response
            disable_buttons();

            // if timeout, set correct to 0
            if (response.timeout) {
              response.correct = 0;
            }

            var trial_data = {
              rt: response.rt,
              timeout: response.timeout,
              correct: response.correct,
              recording: this.recording,
              response: final_response,
              button_clicks: response.button_clicks,
              alert_counter: this.alert_counter,
              choices: response.choices,
              target: response.target,
              trial_duration: response.trial_duration,
              alert_threshold: response.alert_threshold,
              voice_check_frequency: response.voice_check_frequency,
            };

            display_element.innerHTML = "";

            // end trial
            jspsych.finishTrial(trial_data);
          });
        };

        if (isCorrectResponse) {
          // Add a delay of 0.5 seconds before stopping the recording for correct responses
          setTimeout(finishTrial, 500);
        } else {
          // Immediately finish the trial for timeouts
          finishTrial();
        }
      };

      const after_correct_response = (jspsych) => {
        this.end_trial(true);
      };

      const after_timeout = (jspsych) => {
        response.timeout = true;
        this.end_trial(false);
      };

      // end trial if trial_duration is set
      if (trial.trial_duration !== null) {
        this.jsPsych.pluginAPI.setTimeout(after_timeout, trial.trial_duration);
      }
    }

    // functions for recording audio
    setupRecordingEvents(display_element, trial) {
      this.check_inactive = async (data) => {
        const ranges = {
          speech: { min: 85, max: 255 },
        };
        const rangeAnalysis = await processRecordingWithRanges(
          data,
          ranges,
          trial.voice_check_frequency
        );
        const voiceActivity = rangeAnalysis.speech.rangeActivity;
        const totalAverageActivity =
          voiceActivity.reduce((acc, val) => acc + val.averageActivity, 0) /
          voiceActivity.length;

        if (totalAverageActivity < trial.alert_threshold) {
          alert("Remember to say your thoughts aloud!");
          this.alert_counter++;
        }
      };

      this.data_available_handler = (e) => {
        if (e.data.size > 0) {
          this.recorded_data_chunks.push(e.data);
          if (
            trial.voice_check_frequency !== null &&
            this.recorder.state === "recording"
          ) {
            const data = new Blob(this.recorded_data_chunks, {
              type: "audio/webm",
            });
            this.check_inactive(data);
          }
        }
      };

      this.stop_event_handler = () => {
        const data = new Blob(this.recorded_data_chunks, {
          type: "audio/webm",
        });
        this.audio_url = URL.createObjectURL(data);
        const reader = new FileReader();
        reader.addEventListener("load", () => {
          const base64 = reader.result.split(",")[1];
          this.recording = base64;
          this.load_resolver();
        });
        reader.readAsDataURL(data);
      };

      this.start_event_handler = (e) => {
        // resets the recorded data
        this.recorded_data_chunks.length = 0;
        this.recorder_start_time = e.timeStamp;
        // setup timer for ending the trial
        if (trial.trial_duration !== null) {
          this.jsPsych.pluginAPI.setTimeout(() => {
            // this check is necessary for cases where the
            // done_button is clicked before the timer expires
            if (this.recorder.state !== "inactive") {
              this.stopRecording().then(() => {
                if (trial.allow_playback) {
                  this.showPlaybackControls(display_element, trial);
                } else {
                  this.end_trial();
                }
              });
            }
          }, trial.trial_duration);
        }
      };

      this.recorder.addEventListener(
        "dataavailable",
        this.data_available_handler
      );
      this.recorder.addEventListener("stop", this.stop_event_handler);
      this.recorder.addEventListener("start", this.start_event_handler);
    }

    startRecording(freq_s) {
      if (freq_s === null) {
        this.recorder.start();
      } else {
        this.recorder.start(freq_s * 1000);
      }
    }

    stopRecording() {
      this.recorder.stop();
      return new Promise((resolve) => {
        this.load_resolver = resolve;
      });
    }
  }
  jsPsychGameOfNAudioRecording.info = info;

  return jsPsychGameOfNAudioRecording;
})(jsPsychModule);
