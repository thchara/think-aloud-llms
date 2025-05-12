const completionCodeByCorrectCount = {
  0: "C11LHFW4",
  1: "C14JDTNU",
  2: "C1HO5QG8",
  3: "CQRE2YA1",
  4: "C1P71TB8",
  5: "CONF6HTU",
  6: "CS3DFD44",
  7: "C84D2FU1",
  8: "C1OXO3J0",
  9: "C34D99JO",
  10: "C1JGNXHD",
};

/************ Initialize task and data **************************/
var jsPsych = initJsPsych({
  use_webaudio: true,
  show_progress_bar: true,
  auto_update_progress_bar: false,
  on_finish: function () {
    const completion_code = completionCodeByCorrectCount[correct_count];
    window.location =
      "https://app.prolific.com/submissions/complete?cc="+completion_code;
  },
});

const pid = jsPsych.data.getURLVariable("PROLIFIC_PID");
const study_id = jsPsych.data.getURLVariable("STUDY_ID");
const session_id = jsPsych.data.getURLVariable("SESSION_ID");
const exp_type = jsPsych.data.getURLVariable("TYPE") == 1 ? "vp" : "no-vp";
const condition = jsPsych.data.getURLVariable("CONDITION");

if (exp_type == "vp") {
  var trial_type = jsPsychGameOfNAudioRecording;
} else {
  var trial_type = jsPsychGameOfN;
}

jsPsych.data.addProperties({
  pid: pid,
  study_id: study_id,
  session_id: session_id,
  exp_type: exp_type,
  condition: condition,
});

/********************** Helper functions **********************/
function shuffle(array) {
  return jsPsych.randomization.shuffle(array);
}

/********************* stimuli ******************************/

const practice_set = [
  { choices: [6, 1, 1, 2], target: 24, practice: true },
  { choices: [8, 2, 1, 1], target: 24, practice: true },
];

const condition_trials = conditions[condition];

let problem_set = [];
for (let i = 0; i < condition_trials.length; i++) {
  var choices = condition_trials[i];
  var target = 24;
  problem_set.push({ choices: choices, target: target, practice: false });
}

problem_set = shuffle(problem_set);

/********************** main task and practice  *************************/

var initial_audiotrial_in_sequence = true;
var correct_count = 0;
const exp_length = 10 + practice_set.length + 6;

var pre_problem_middle = {
  on_start: function (trial) {
    if (exp_type == "vp") {
      trial.pages = [
        '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">You may rest your voice for a moment. <br> Press continue when you are ready to proceed with the next problem and continue recording. <br>',
      ];
    } else {
      trial.pages = [
        '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Press continue when you are ready to proceed with the next problem. <br>',
      ];
    }
  },
  pages: [""],
  type: jsPsychInstructions,
  show_clickable_nav: true,
  button_label_next: "Continue",
};

var pre_problem_middle_conditional = {
  timeline: [pre_problem_middle],
  conditional_function: function () {
    if (initial_audiotrial_in_sequence) {
      return false;
    } else {
      return true;
    }
  },
};

var pre_problem_initial = {
  on_start: function (trial) {
    if (exp_type == "vp") {
      trial.pages = [
        '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Press continue when you are ready to proceed with the next problem and begin recording.',
      ];
    } else {
      trial.pages = [
        '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Press continue when you are ready to proceed with the next problem.',
      ];
    }
  },
  pages: [""],
  type: jsPsychInstructions,
  show_clickable_nav: true,
  button_label_next: "Continue",
  on_finish: function () {
    initial_audiotrial_in_sequence = false;
  },
};

var pre_problem_initial_conditional = {
  timeline: [pre_problem_initial],
  conditional_function: function () {
    if (initial_audiotrial_in_sequence) {
      return true;
    } else {
      return false;
    }
  },
};

var pre_problem = {
  timeline: [pre_problem_middle_conditional, pre_problem_initial_conditional],
};

var gameTrial = {
  on_start: function (trial) {
    trial.html = "<b>Target number: " + String(trial.target) + "</b><br><br>";
    jsPsych.setProgressBar(jsPsych.getProgressBarCompleted() + 1 / exp_length);
  },
  type: trial_type,
  html: "",
  trial_duration: 180000,
  choices: jsPsych.timelineVariable("choices"),
  target: jsPsych.timelineVariable("target"),
  alert_threshold: 3,
  data: {
    type: "gameTrial",
    practice: jsPsych.timelineVariable("practice"),
  },
  on_finish: function(data) {
    if (!jsPsych.timelineVariable("practice")) {
      correct_count += data.correct;
    }
  },
};

var loop_practice_trial = false;

var feedback = {
  type: jsPsychInstructions,
  on_start: function (trial) {
    timeout = jsPsych.data.getLastTrialData().trials[0].timeout;
    target = jsPsych.data.getLastTrialData().trials[0].target;
    if (timeout == false) {
      trial.pages = ["Correct! You have reached " + target + "! Well done!"];
      if (jsPsych.timelineVariable("practice")) {
        loop_practice_trial = false;
      }
    } else if (!jsPsych.timelineVariable("practice")) {
      trial.pages = ["Unfortunately you ran out of time..."];
    } else {
      trial.pages = [
        "Unfortunately you ran out of time... <br> Please try again.",
      ];
      trial.button_label_next = "Try Again";
      loop_practice_trial = true;
    }
  },
  pages: [""],
  show_clickable_nav: true,
};

var verbalizing_level = [
  "Not at all",
  "Few thoughts",
  "Approximately half",
  "Most thoughts",
  "Every thought",
];

var post_trial_verbalization_answer = 0;

var post_trial_verbalization = {
  type: jsPsychSurveyLikert,
  questions: [
    {
      prompt:
        "To what extent were you saying your thoughts out loud over the last trial? (your answer does not impact your compensation)",
      name: "verbalize",
      labels: verbalizing_level,
    },
  ],
  randomize_question_order: true,
  on_finish: function (data) {
    post_trial_verbalization_answer = data.response["verbalize"];
  },
};

var post_trial_verbalization_feedback = {
  type: jsPsychHtmlButtonResponse,
  stimulus:
    '<p style="max-width: 68%;margin-left: auto; margin-right: auto;"> Please verbalize more of your thoughts!</p>',
  choices: ["Continue"],
};

var post_trial_verbalization_feedback_conditional = {
  timeline: [post_trial_verbalization_feedback],
  conditional_function: function () {
    if (post_trial_verbalization_answer <= 2) {
      return true;
    } else {
      return false;
    }
  },
};

if (exp_type == "vp") {
  var practice_procedure_loop = {
    timeline: [
      pre_problem,
      gameTrial,
      feedback,
      post_trial_verbalization,
      post_trial_verbalization_feedback_conditional,
    ],
    loop_function: function (data) {
      if (loop_practice_trial) {
        return true;
      } else {
        return false;
      }
    },
  };
  var main_procedure = {
    timeline: [
      pre_problem,
      gameTrial,
      feedback,
      post_trial_verbalization,
      post_trial_verbalization_feedback_conditional,
    ],
    // array of indices
    timeline_variables: problem_set,
  };
} else {
  var practice_procedure_loop = {
    timeline: [pre_problem, gameTrial, feedback],
    loop_function: function (data) {
      if (loop_practice_trial) {
        return true;
      } else {
        return false;
      }
    },
  };

  var main_procedure = {
    timeline: [pre_problem, gameTrial, feedback],
    timeline_variables: problem_set,
  };
}

var practice_procedure = {
  timeline: [practice_procedure_loop],
  timeline_variables: practice_set,
};

/********************** setup and instructions **************/

var initialize_mic = {
  type: jsPsychInitializeMicrophone,
  on_finish: function () {
    jsPsych.setProgressBar(jsPsych.getProgressBarCompleted() + 1 / exp_length);
  },
};

var initialize_mic_conditional = {
  timeline: [initialize_mic],
  conditional_function: function () {
    if (exp_type == "vp") {
      return true;
    } else {
      return false;
    }
  },
};

if (exp_type == "vp") {
  var instructions = {
    type: jsPsychInstructions,
    pages: [
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Welcome to the experiment! Click next to begin.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Please read these instructions carefully.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">In this experiment, you will be presented with math problems.<br><br>Each problem has a <b>target number, 24</b>, and several input numbers.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Your task is to combine the input numbers using arithmetic operations (x, /, +, -) and brackets to make 24.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">You must use all input numbers. Reaching 24 without using all input numbers <b>does not</b> count as solving the task. <br><br> Additionally, you will only be able to use each input number <b>once</b>, but you can use the arithmetic operations as you wish.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;"><b>Importantly</b>, while you solve the task, try to say out loud everything that goes through your mind.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;"><b>Example:</b><br><br><b>Target Number: 24</b><br>Input numbers: 13,1,1,2 <br><br>(13-1)x1x2=24<br><br> And so we managed to make 24!',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">The main task will consist of 10 trials.<br><br> You will have a maximum of three minutes to solve each problem.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;"> You will not be able to advance in a trial <b>until you answer correctly</b> (or 3 minutes pass).<br><br>Additionally, you will <b>earn a bonus</b> for each trial in which you answer correctly, with the maximum bonus being $1.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Before the main task begins, there will be two practice trials.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Remember, as you solve the problems, try to say out loud what comes to your mind. <br><br> If you are silent for a long period of time, we will send you a reminder to speak out loud.',
    ],
    show_clickable_nav: true,
    on_finish: function () {
      jsPsych.setProgressBar(
        jsPsych.getProgressBarCompleted() + 1 / exp_length,
      );
    },
  };
} else {
  var instructions = {
    type: jsPsychInstructions,
    pages: [
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Welcome to the experiment! Click next to begin.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Please read these instructions carefully.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">In this experiment, you will be presented with math problems.<br><br>Each problem has a <b>target number, 24</b>, and several input numbers.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Your task is to combine the input numbers using arithmetic operations (x, /, +, -) and brackets to make 24.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">You must use all input numbers. Reaching 24 without using all input numbers <b>does not</b> count as solving the task. <br><br> Additionally, you will only be able to use each input number <b>once</b>, but you can use the arithmetic operations as you wish.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;"><b>Example:</b><br><br><b>Target Number: 24</b><br>Input numbers: 13,1,1,2 <br><br>(13-1)x1x2=24<br><br> And so we managed to make 24!',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">The main task will consist of 10 trials.<br><br> You will have a maximum of three minutes to solve each problem.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">You will not be able to advance in a trial <b>until you answer correctly</b> (or 3 minutes pass).<br><br>Additionally, you will <b>earn a bonus</b> for each trial in which you answer correctly, with the maximum bonus being $1.',
      '<p style="max-width: 68%;margin-left: auto; margin-right: auto;">Before the main task begins, there will be two practice trials.',
    ],
    show_clickable_nav: true,
    on_finish: function () {
      jsPsych.setProgressBar(
        jsPsych.getProgressBarCompleted() + 1 / exp_length,
      );
    },
  };
}

var pre_task = {
  type: jsPsychInstructions,
  pages: ["Now, the real task will begin."],
  show_clickable_nav: true,
  on_finish: function () {
    jsPsych.setProgressBar(jsPsych.getProgressBarCompleted() + 1 / exp_length);
    initial_audiotrial_in_sequence = true;
  },
};

/************* post experiment questionnairre and debrief *******/

var likert_scale = [
  "Strongly Disagree",
  "Disagree",
  "Neutral",
  "Agree",
  "Strongly Agree",
];

var IRQ_verbal = {
  type: jsPsychSurveyLikert,
  preamble: "Please respond the the following statements as they refer to you:",
  questions: [
    {
      prompt:
        "When I think about someone I know well, I instantly hear their voice in my mind.",
      name: "1",
      labels: likert_scale,
      required: true,
    },
    {
      prompt:
        "I think about problems in my mind in the form of a conversation with myself.",
      name: "2",
      labels: likert_scale,
      required: true,
    },
    {
      prompt:
        "If I am walking somewhere by myself, I often have a silent conversation with myself.",
      name: "3",
      labels: likert_scale,
      required: true,
    },
    {
      prompt:
        "If I am walking somewhere by myself, I frequently think of conversations that I’ve recently had.",
      name: "4",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "My inner speech helps my imagination.",
      name: "5",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "I tend to think things through verbally when I am relaxing.",
      name: "6",
      labels: likert_scale,
      required: true,
    },
    {
      prompt:
        "When thinking about a social problem, I often talk it through in my head.",
      name: "7",
      labels: likert_scale,
      required: true,
    },
    {
      prompt:
        "I like to give myself some down time to talk through thoughts in my mind.",
      name: "8",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "I hear words in my 'mind’s ear' when I think.",
      name: "9",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "I rarely vocalize thoughts in my mind.",
      name: "10r",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "I often talk to myself internally while watching TV.",
      name: "11",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "My memories often involve conversations I’ve had.",
      name: "12",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "The word ‘hotel’ has three letters.",
      name: "ac1",
      labels: likert_scale,
      required: true,
    },
    {
      prompt: "Elephants are larger than dogs.",
      name: "ac2",
      labels: likert_scale,
      required: true,
    },
  ],
  randomize_question_order: true,
  on_finish: function(){
    jsPsych.setProgressBar(jsPsych.getProgressBarCompleted() + 1 / exp_length);
  }
};

var difficulty_and_experience_qs = {
  type: jsPsychSurveyLikert,
  questions: [
    {
      prompt: "How difficult was this experiment?",
      labels: [
        "Easy",
        "Slightly difficult",
        "Moderately difficult",
        "Difficult",
        "Very difficult",
      ],
      required: true,
      name: "difficulty",
    },
    {
      prompt:
        "Have you played a game like this, where you need to combine a set of numbers to make a target number, before?",
      labels: [
        "No experience",
        "Slight experience <br> (played 1-2 times)",
        "Moderate experience <br> (played 3-10 times)",
        "Substantial experience <br> (played more than 10 times)",
      ],
      required: true,
      name: "prior experience",
    },
  ],
  on_finish: function(){
    jsPsych.setProgressBar(jsPsych.getProgressBarCompleted() + 1 / exp_length);
  }
};

var postExperimentSurvey = {
  type: jsPsychSurveyText,
  preamble:
    "<p>Thank you for taking part in the experiment.</p><p>You will be redirected to Prolific after this survey. Please do not navigate away from this page.</p>",
  questions: [
    {
      prompt:
        "Please describe the strategy you used to answer the questions in this experiment.",
      rows: 6,
      columns: 50,
      name: "strategy",
      required: true,
    },
    {
      prompt: "Were any of the instructions unclear?",
      rows: 6,
      columns: 50,
      name: "instructions",
      required: true,
    },
    {
      prompt:
        "What did you think about the experiment's interface (using the buttons to input your answer), was it intuitive?",
      rows: 6,
      columns: 50,
      name: "interface",
      required: true,
    },
    {
      prompt:
        "Please give any feedback you have about the experiment, including problems encountered.",
      rows: 6,
      columns: 50,
      name: "feedback",
      required: true,
    },
  ],
  on_finish: function(){
    jsPsych.setProgressBar(jsPsych.getProgressBarCompleted() + 1 / exp_length);
  }
};

var debrief = {
  type: jsPsychInstructions,
  pages: [
    'Thank you for your participation in the experiment! <br> In this experiment, we attempted to examine the problem-solving strategies people use to search for the answer to mathematical problems like the ones you encountered. <br> Some participants provided "thinking aloud" responses in which they verbalized their thoughts as they were solving the game. These responses will help us understand the mental processes underlying problem-solving in this game. Other participants simply played the game without having to speak out loud. Data from these participants will help us understand whether there are differences between solving problems while voicing inner speech and without doing so. <br> For more information about our lab and research, visit https://cocolab.stanford.edu/<br>Thank you again for your participation!',
  ],
  show_clickable_nav: true,
  on_finish: function () {
    jsPsych.setProgressBar(1);
  },
};

/****************** * initialize timeline and execute task *********/

const timeline = [
  initialize_mic_conditional,
  instructions,
  practice_procedure,
  pre_task,
  main_procedure,
  IRQ_verbal,
  difficulty_and_experience_qs,
  postExperimentSurvey,
  debrief,
];
jsPsych.run(timeline);
