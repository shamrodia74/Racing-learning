from datetime import datetime
import os
from game import Game
from pygame import Vector2
from inputs import Inputs
import game_loops
import genetic
import pygame
import numpy as np
import utils
from constants import MAX_FRAMES_PENALTY, game_params, model_params
import matplotlib.pyplot as plt

sep = os.path.sep
now = datetime.now()
dt_string = now.strftime("%d_%m_%Y-%H_%M")
vectors = game_params["vectors"]

# vectors = [Vector2(0.,-1),Vector2(1,-1),
#	Vector2(1,-0.5),Vector2(1,0.),
#	Vector2(1,0.5),Vector2(1,1),Vector2(0.,1)]
# neural_structure = mode_params["neural_structure"]
n_frames = 0
# epsilon = 1e-3
# max_idle = 20
save_path_gen = "."+sep+"gens"+sep
save_path_models = "."+sep+"models"+sep
save_path_figs = "."+sep+"gens"+sep+"figures"+sep
print(save_path_gen)
neural_structure = model_params["neural_structure"]
init_chromo = genetic.generate_chromos_from_struct(neural_structure)
print(neural_structure)
def fit_function(indiv, model, max_frames=game_params["max_frames"]):
	def decision(state_vector):
		output_net = model.predict(x=np.array(state_vector).reshape(-1, len(state_vector)))
		decision_input = utils.net_to_input(output_net[0])
		return decision_input

	game = Game(vectors)
	score = 0
	n_idle = 0 
	t = 0
	while t < max_frames:
		pygame.event.get()
		network_inputs = game.get_agent_inputs()
		if np.abs(network_inputs).all()<game_params["epsilon"]:
			n_idle += 1
			if n_idle >= game_params["max_idle"]:
				score -= MAX_FRAMES_PENALTY
				break
		else:
			n_idle = 0
		inputs = decision(network_inputs)
		reward, running = game.run(inputs, is_ai=True)
		t += 1
		if reward > 0:
			t = 0
		score += reward
		if not running:
			break

	if t>=max_frames-1:
		score -= MAX_FRAMES_PENALTY/(game.checkpoint+1)
	print(score)
	return score

model = genetic.Genetic(model_params["n_indiv"], neural_structure, fit_function)
# loaded_gen = genetic.load_gen(".\\gens\\04_02_2020-17_10_0.hdf5", fit_function)
# model.generations = [loaded_gen]
mutation_start = model_params["mutation_start"]
mutation_stop = model_params["mutation_stop"]
n_epochs = model_params["n_epochs"]
mutation_decay = (mutation_stop -mutation_start)/n_epochs
best_score = -1000.
n_bests = model_params["n_bests"]
# weights_off = [n_bests - (2*i/n_bests) for i in range(n_bests)]
weights_off = model_params["weights"]
keep_n_bests = model_params["keep_n_bests"]
scores = []

def plot_scores(scores, filename):
	means = []
	maxs = []
	mins = []
	for gen in scores:
		means.append(np.mean(gen))
		maxs.append(np.max(gen))
		mins.append(np.min(gen))
	plt.figure(figsize=(10,10))
	plt.subplot(1,3,1)
	plt.plot(means, label="Score moyen")
	plt.title("Evolution du score moyen")
	plt.xlabel("Generation")
	plt.ylabel("Score")
	plt.legend()
	plt.subplot(1,3,2)
	plt.plot(maxs, label="Score max")
	plt.title("Evolution du score max")
	plt.xlabel("Generation")
	plt.ylabel("Score")
	plt.legend()	
	plt.subplot(1,3,3)
	plt.plot(mins, label="Score min")
	plt.title("Evolution du score min")
	plt.xlabel("Generation")
	plt.ylabel("Score")
	plt.legend()
	plt.tight_layout()
	plt.savefig(filename)

for i in range(n_epochs):
	filename_fig = save_path_figs + dt_string + "_gen_"+str(i)+".png"
	if (i+1)%5==0:
		plot_scores(scores, filename_fig)
	print("===== Generation {} =====".format(i))
	filename_g = save_path_gen + dt_string +"_"+ str(i)
	filename_m = save_path_models + dt_string
	mutation_chance = mutation_start + i*mutation_decay
	print("epsilon = ", mutation_chance)
	gen = model.train(mutation_chance=mutation_chance, n_bests=n_bests,
	 weights=weights_off, keep_n_bests=keep_n_bests)

	last_gen = model.generations[-2]
	best_scores = last_gen.best_scores(n_firsts=last_gen.n_individus)
	print("best scores = ", best_scores[:n_bests])
	scores.append(best_scores)
	if best_scores[0] >= best_score:
		best_indiv = last_gen.individuals[last_gen.rank_fitness()[0]]
		best_indiv.save_model(filename_m 
			+ "_s_"+ str(int(best_indiv.fitness))+".hdf5")
		last_gen.save_gen(filename_g+".hdf5")
		best_score = best_scores[0]
	



