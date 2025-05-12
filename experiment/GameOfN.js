var jsPsychGameOfN = (function (jspsych) {
  "use strict";

  const info = {
    name: "GameOfN",
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
    },
  };

  /**
   * **GameOfN**
   *
   *
   * @author Daniel Wurgaft
   */
  class jsPsychGameOfN {
    constructor(jsPsych) {
      this.jsPsych = jsPsych;
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

      this.end_trial = () => {
        // measure rt
        var endTime = performance.now();
        var rt = Math.round(endTime - startTime);
        var final_response = document.getElementById("input").value;

        console.log("end trial");

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
          response: final_response,
          button_clicks: response.button_clicks,
          choices: response.choices,
          target: response.target,
          trial_duration: response.trial_duration,
        };

        display_element.innerHTML = "";

        // end trial
        jspsych.finishTrial(trial_data);
      };

      const after_correct_response = (jspsych) => {
        this.end_trial();
      };

      const after_timeout = (jspsych) => {
        response.timeout = true;
        this.end_trial();
      };

      // end trial if trial_duration is set
      if (trial.trial_duration !== null) {
        this.jsPsych.pluginAPI.setTimeout(after_timeout, trial.trial_duration);
      }
    }
  }
  jsPsychGameOfN.info = info;

  return jsPsychGameOfN;
})(jsPsychModule);
