# --------------------------
# This is the objective of the story.  It is used to help guide the story creation process.
# The whole point is to create a coherent story that meets the objective, beyond the 4K token limit that most LLMs have.

client_objective = """- Genre: Isekai Humour
- Target audience: young adult
- Target number of chapters: 5
- Target length of each chapter: 5000 words
- Setting: A minecraft world
- Tropes: The main character thinks she is incapable of doing anything, but is actually the most powerful person in the world
- Sensitivity: must be safe for work"""

# --------------------------
# Imports
import json
import re
import requests


class Ollama:
    """
    A class to interact with a local LLM service using the Ollama.ai

    Format is either None or "json"
    """

    def __init__(self, *, system_prompt, model="qwen2.5:14b", tokens=20000):
        self.system_prompt = system_prompt
        self.model = model
        self.tokens = tokens

    def tokens(self):
        return self.tokens

    def json(self, text, temperature=0.0, format="json"):
        return self.process(text, temperature, format)

    def process(self, text, temperature=0.0, format=None):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": self.system_prompt},
                {"role": "assistant", "content": "Understood"},
                {"role": "user", "content": text},
            ],
            "options" : {"temperature":temperature},
            "stream": False,
        }
        if format:
            payload["format"] = format

        response = requests.post("http://localhost:11434/api/chat", data=json.dumps(payload), stream=False)
        return response.json().get("message", {}).get("content","").strip()

llm_service = Ollama(system_prompt="")


# --------------------------
# Global variable to track all communication during the story generation process

all_transcripts = []


# --------------------------
# The output from each meeting is stored in this dictionary.
# Each agent has the ENTIRE contents pasted at the top of each meeting they attend so they can reference it.
# By the end of the story creation process it will have the plot, characters, setting, and chapter outline
# with estimated words per chapter, chapter summaries, and the chapters themselves.  Everything that was generated from a meeting

task_output = {}

try :

    with open("output/story.json","r") as file:
        data = json.load(file)
        all_transcripts = data['transcript']
        task_output = data['creative']
except:
    pass


# --------------------------
# This function is called to perform a task.  It is called for each task in the story.

def do_task(task, agents, client_objective, task_output):
    if task['name'] in task_output:
        print(f"Skipping {task['name']} because it is already completed")
        return

    format = task.get("format",None)
    name = task['name']
    output = task['output']
    print("="*10,name,"="*10)

    target_word_count = 1 if '(' not in name else int(name.split("(")[1].split(' ')[0])

    meeting = f"I am in a meeting named: {task['name']}"

    agent = agents[task['attendees'][0]]
    initial_agent_direction = task.get("initial_agent_direction",f"[{agent['title']}] The objective for is meeting is to define the {task['output']} of the story.")

    transcript = ["We all know the writing assignments constraints are:",
                  client_objective,
                  format_task_output(task_output), initial_agent_direction
                  ]
    all_transcripts.append(transcript)

    attendees = task['attendees'][1:] # + task['attendees'] if task.get("loop",True) else task['attendees'][1:]
    for attendee in attendees:
        agent = agents[attendee]
        other_attendees = [f"[{agents[attendee]['title']}] Hi, {agents[attendee]['description']}" for attendee in task['attendees'] if attendee != agent['title']]
        agent_prompt = [agent['description'], meeting, "The attendees are:", *other_attendees, *transcript]
        # it is the facilitator.  They check if we are done or if we need to proceed
        if attendee == task['attendees'][0]:
            agent_prompt = "\n\n".join([*agent_prompt, f"[{agent['title']}] " + f"Am I ready to define the {task['output']} of the story and it meets all the assignment constraints (yes or no)?"])
            agent_response = llm_service.process(agent_prompt, agent['temperature'], format=format)
            if 'yes' in agent_response.lower():
                break
            else:
                transcript.append(f"[{agent['title']}] We need to agree on the {task['output']} of the story.  Let's move towards agreeing on one that aligns with the assignment constraints.")

        else:
            print("-"*10, agent['title'], "-"*10)
            agent_prompt = "\n\n".join([*agent_prompt, f"[{agent['title']}] " + task.get("agent_prompt","Although I may have a lot to say, I'll keep my response to at most a few sentences.  My response is:\n")])

            agent_response = ""

            no_end_found = True
            while no_end_found and len(agent_response.split(" ")) < target_word_count * 1.25:
                sub_response = llm_service.process(agent_prompt + agent_response, agent['temperature'], format=format)
                if 'END ' in sub_response:
                    print("-"*10, "Found END", "-"*10)
                    agent_response += sub_response.split("END ")[0]
                    no_end_found = False
                    break
                else:
                    agent_response += sub_response

            transcript.append(f"[{agent['title']}] {agent_response}")
            print(agent_response)

    if task.get("loop",True):
        finalize_task = task.get("finalize_task",f"Without adding commentary, I will note for my records that from the above conversation the {task['output']} of the story.  This will be the only record so I will pay close attention to preserving all related important information:\n")

        agent = agents[task['attendees'][0]]
        print("-"*10, agent['title'], "-"*10)

        other_attendees = [f"[{agents[attendee]['title']}] Hi, {agents[attendee]['description']}" for attendee in task['attendees'] if attendee != agent]
        agent_prompt = [agent['description'], meeting, "The attendees are:", *other_attendees, *transcript]

        agent_prompt = "\n\n".join([*agent_prompt,finalize_task])
        agent_response = llm_service.process(agent_prompt, agent['temperature'], format=format)

        transcript.append(f"[{agent['title']}] " + finalize_task + agent_response)
        print(agent_response)

    task_output[output] = agent_response
    print("")


# --------------------------
# This function is called to create agents.  Each agent has a different personality and role in meetings

def create_agents():
    agents = [
        {"title":"CEO", 
         "description":"""I am the CEO of ChatWriter.
My main responsibilities include being an active decision maker on user demands and other key policy issues, leader, manager, and executor. 
My decision-making role involves high-level decisions about policy and strategy;
and my communicator role can involve speaking to the organization's management and employees.""",
    "temperature":0.01},
        {"title":"Artistic Director",
         "description" : """I am the Artistic Director of ChatWriter.  I am very familiar with story writing.
I will make high-level decisions for the overarching story that closely aligh with the organiation's goals,
while I work alongside the organizations writing staff members to perform everyday operations.""",
    "temperature":1.0},
        {"title":"Professional Writer",
         "description": """I am a Professional Writer of ChatWriter.
I can write and create coherent interesting and engaging stories where characters seem to come to life.
I have extensive writing experience and understand that characters in my writing should not be omniscient or flawless,
and indeed the interesting story plays on the characters flaws and lack of knowledge.""",
    "temperature":0.5},
        {"title":"Editor",
         "description": """I am an Editor of ChatWriter.
I can help writers to assess their writing quality and give feedback on pacing, continuity, focus, development, coherence, 
logical errors, grammatical errors, overused cliches, and offer proposals to improve their writing.""",
    "temperature":0.2}
    ]

    # convert to dictionary by title
    agents = dict( (a['title'], a) for a in agents)
    return agents

agents = create_agents()


# --------------------------
# This function is called to create the initial tasks, such as creating the plot, characters, and setting
# New tasks can be added during the story creation process, and specifically the task of writing each chapter
# is added after the outline is created.  Tasks are completed by having "meetings" with the agents.

def create_initial_tasks():
    tasks = [
        {
            "name" : "Brainstorming the story plot",
            "attendees" : ["CEO", "Artistic Director", "Professional Writer"],
            "output" : "Plot"
        }
    ]

    for part in "Characters with names with descriptions, Conflict, Setting".split(", "):
        tasks.append({
            "name" : f"Brainstorming the story line {part}",
            "attendees" : ["CEO", "Artistic Director", "Professional Writer"],
            "output" : part
        })

    for part in "Exposition, Climax, Resolution".split(", "):
        tasks.append({
            "name" : f"Brainstorming the plot {part}",
            "attendees" : ["CEO", "Artistic Director", "Professional Writer"],
            "output" : part
        })

    tasks.append({
        "name" : "Chapter outline",
        "attendees" : ["Editor", "Professional Writer"],
        "output" : "chapter outline with estimated words per chapter",
        "agent_prompt" : "My response is:\n",
        "format" : "json",
        "finalize_task" : """From the above conversation I believe we can define the chapter outline with estimated words per chapter.
In order to help keep the format of the outline consistent I will convert it to json format that mimics this example

{
  "estimated words per chapter": 1500,
  "chapters" : [
    "Our hero meets receives a letter",
    "A surprise visit during the grand feast",
    "The Empress is none too please with how the feast is going",
    "The Fool is the fool but isn't fooled"
    ] 
}

The chapter outline with estimated words per chapter is:\n"""
    })
    return tasks

tasks = create_initial_tasks()


# --------------------------
# The rest of these function are focused on running the meetings to complete the tasks,
# formatting output, and scheduling the agents participation in the meetings

def format_task_output(task_output):
    if len(task_output) > 0:
        return "We all know that our creative process has produced this so far:\n" + "\n".join([f"- {key}: {value}" for (key,value) in task_output.items()])
    else:
        return ""


def create_copy_of_tasks(index, chapters, task_output):
    copy_task_output = dict(task_output)
    MAX_CHAPTERS = 10
    if index > MAX_CHAPTERS:
        for i in range(0, index-MAX_CHAPTERS):
            if chapters[i] in copy_task_output:
                del copy_task_output[chapters[i]]
        for i in range(index-MAX_CHAPTERS,index):
            if f"summary of {chapters[i]}" in copy_task_output:
                del copy_task_output[f"summary of {chapters[i]}"]
    return copy_task_output

def process_chapter(index, chapters, task_output):
    chapter = chapters[index]
    task = {
        "name" : f"Write {chapter}",
        "attendees" : ["CEO", "Professional Writer"],
        "output" : chapter,
        "initial_agent_direction" : f"""[CEO] The objective for this meeting is to write '{chapter}'.
Please write this chapter in its entirety.    When I am done the summary I'll write the exact phrase 'END CHAPTER'.  Use an active voice, write in the first person from the main characters point of view, and put conversation in quotes.""",
        "agent_prompt" : f"I'll start right now.  My response is:\n\n{chapter}\n\nBEGIN CHAPTER\n",
        "loop" : False
    }
    tasks.append(task)

    copy_task_output = create_copy_of_tasks(index, chapters, task_output)

    do_task(task, agents, client_objective, copy_task_output)
    # using copy task output, so copy the chapter to the task output
    task_output[chapter] = copy_task_output[chapter]


def process_summary(index, chapters, task_output):
    chapter = chapters[index]
    summary_of_chapter = f"summary of {chapter}"
    task = {
        "name" : f"Summarize {chapter}",
        "attendees" : ["CEO", "Professional Writer"],
        "output" : summary_of_chapter,
        "loop" : False,
        "initial_agent_direction" : f"""[CEO] The objective for this meeting is to summarize '{chapter}'.
Please write a short summary of this chapter so that we can quickly reference the import points without having to re-read the entire thing.""",
        "agent_prompt" : "I'll start right now.  When I am done the summary I'll write the exact phrase 'END SUMMARY'.  My response is:\n\nShort summary of {chapter}\n\nBEGIN SUMMARY\n",
    }
    tasks.append(task)

    copy_task_output = create_copy_of_tasks(index, chapters, task_output)

    do_task(task, agents, client_objective, copy_task_output)
    # using copy task output, so copy the chapter to the task output
    task_output[summary_of_chapter] = copy_task_output[summary_of_chapter]


chapters = []
def generate_content():

    for task in tasks:
        yield do_task(task, agents, client_objective, task_output)

    chapters.extend(task_output["chapter outline with estimated words per chapter"].split('\n'))

    for index in range(len(chapters)):
        if 'Chapter ' in chapters[index] and ' words)' in chapters[index]:
            yield process_chapter(index, chapters, task_output)
            yield process_summary(index, chapters, task_output)


# --------------------------
# And FINALLY generate all the output!

try:
    content = generate_content()
    for item in content:
        pass
except:
    pass

# --------------------------
# And write the story to a file

with open("output/story.txt", "w") as file:
    for chapter in chapters:
      file.write( "\n\n-- " + re.sub('\\(.*','',chapter) + " --\n\n" )
      file.write( task_output[chapter] )

# --------------------------
# And write all communication to and between agents to a debug file

with open("output/story.json","w") as file:
   json.dump({'transcript':all_transcripts, 'creative':task_output}, file, indent=4)

# --------------------------
# Write all the content to a content file

with open("output/task_output.json","w") as file:
    json.dump(task_output, file, indent=4)
