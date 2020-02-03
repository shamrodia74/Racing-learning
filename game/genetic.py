import numpy as np
import copy
import os
import sys
from itertools import combinations
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # or any {'0', '1', '2'}
import tensorflow as tf
tf.logging.set_verbosity(tf.logging.ERROR)
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
from keras.layers import Dense, Activation
from keras.models import Sequential
import h5py


"""
Implémentation d'un algorithme génétique apprenant les poids d'un réseau de neurones densément connecté
"""

class Chromosome:
	"""
	Un chromosome est un ensemble de gènes, un chromosome représente les caractéristiques d'un perceptrop.
	Les gènes sont les poids entre les neurones de la couche précédente et lui-même, 
	avec un poids représentant le biais
	"""
	def __init__(self, size, gene_list=[], random_init=True, start_range=-1, end_range=1):
		"""Constructeur d'un chromosome
		Un chromosome est une liste de gènes dont les valeurs sont comprises dans un intervalle.
		Pour définir un réseau de neurones, il faut une liste de liste de chromosomes. 
		On a donc [Couche1, Couche2, ...] où chaque couche est une liste de chromosomes 
		correspondant à chaque neurone de cette couche.
		Args:
			size (int): longueur de la liste
			gene_list (list): valeur des gènes si connus à l'avance, si vide on en génère aléatoirement
			random_init (bool): si True, gènes choisis aléatoirement, sinon initialisés à 0
			start_range (float): borne inférieur de l'intervalle
			end_range (float): borne supérieur de l'intervalle

		Returns:
			Chromosome : Liste de gènes
		"""
		# gestion des inputs 
		if start_range > end_range:
			self.start_range = end_range
			self.end_range = start_range
		else:
			self.start_range = start_range
			self.end_range = end_range

		if len(gene_list) == size:
			# clipping de la liste pour s'assurer d'etre bien dans l'intervalle donne
			self.genes = [max(min(end_range, gene_list[i]), start_range) for i in range(size)]
			
		elif random_init:
			self.genes = start_range + np.random.rand(size)*(end_range-start_range)
		else:
			self.genes = np.zeros(size)

		self.genes = np.array(self.genes)


# ====== Définition de fonctions utiles pour gérer les chromosomes =====

def chromo_to_weights(chromos):
	""" Convertir chromosomes en poids pour réseau de neurones
	Fonction qui prend en entrée une liste de liste de chromosomes et retourne une ensemble de poids
	que Keras peut utiliser comme poids d'un réseau de neurones.

	Args:
		chromos (list(list(Chromosome))) : Liste de liste de chromosomes qui représente le réseau de neurones

	Returns:

		numpy array: matrice des poids sous une forme lisible directement par Keras 

	"""
	weights_list = []
	for chromo in chromos:
		listed_chromos = np.array([x.genes for x in chromo], dtype=float)
		weights = [listed_chromos[:, :-1].T, listed_chromos[:,-1]]
		weights_list = weights_list + weights
	return weights_list

def weights_to_chromos(weights, start_range=-1, end_range=-1):
	""" Conversion poids d'un réseau en chromosomes
	Fonction inverse de chromo_to_weights, permet de générer les chromosomes d'un Individu
	à partir des poids de son réseau

	Args:


	
	"""
	i = 0
	list_chromos = []
	while i<len(weights):
		current_array = weights[i].T
		current_array = np.c_[current_array, weights[i+1]]
		chromos = []
		for l in current_array:
			chromo = Chromosome(len(l), gene_list = l, start_range=start_range, end_range=end_range, random_init=False)
			chromos.append(chromo)
		i += 2
		list_chromos.append(chromos)
	return list_chromos

	
def generate_chromos_from_struct(neural_structure):
	chromos = []
	for i in range(len(neural_structure)-1):
		chromos_layer = []
		for j in range(neural_structure[i+1]):
			chromos_layer.append(Chromosome(neural_structure[i]+1)) # nb connexions + biais
		chromos.append(chromos_layer)
	return chromos

class Individu:
	"""
	La fit_function est la fonction de fitness qui doit etre codee de maniere
	a avoir un individu en entree et donc de creer la structure adaptee pour ensuite 
	calculer le score.
	"""
	def __init__(self, neural_structure, fit_function):
		self.chromos = generate_chromos_from_struct(neural_structure)
		self.fitness = np.random.random()
		self.fit_function = fit_function
		self.weights = np.array(chromo_to_weights(self.chromos))

	def update_fitness(self, model):
		model.set_weights(self.weights)
		self.fitness = self.fit_function(self, model)

	def copy(self):
		new = copy.deepcopy(self)
		new.chromos = copy.deepcopy(self.chromos)
		new.fitness = copy.deepcopy(self.fitness)
		new.weights = copy.deepcopy(self.weights)
		return new

class Population:

	def __init__(self, n_individus, neural_structure, fit_function, individuals=None):
		self.individuals = list()
		if not individuals or len(individuals) != n_individus:
			for i in range(n_individus):
				indiv = Individu(neural_structure, fit_function)
				self.individuals.append(indiv.copy())
				# print(hex(id(self.individuals)))
		else:
			self.individuals = np.array(individuals)

		self.n_individus = n_individus
		self.structure = neural_structure # [n_inputs, n_neurons_layer1, n_neurons_layer2, ..., n_outputs]


	def fit(self, model):
		for i in range(len(self.individuals)):
			print(str(i+1)+"/"+str(len(self.individuals)))
			self.individuals[i].update_fitness(model)

	def rank_fitness(self):
		fitness = [indiv.fitness for indiv in self.individuals]
		sort = np.argsort(fitness)[::-1]
		return sort

	def best_scores(self, n_firsts=1):
		rank = np.array(self.rank_fitness())
		n_firsts = min(n_firsts, self.n_individus)
		# print("n_firsts = ", n_firsts)
		# print("rank= ", rank)
		sorted_indiv = np.array(self.individuals)[rank]
		return [indiv.fitness for indiv in sorted_indiv[:n_firsts]]



def get_weights_per_couple(weights_per_parent, n_parents):
	idx_combi = [i for i in combinations(np.arange(n_parents), 2)]
	weights_per_couple = [weights_per_parent[p[0]]*weights_per_parent[p[1]] for p in idx_combi]
	weights_per_couple = np.array(weights_per_couple)/np.sum(weights_per_couple)
	return weights_per_couple

def get_offspring_per_couple(weights_per_couple, n_individus):
	offspring_per_couple = []
	count = 0
	for w in weights_per_couple:
		n_offspring = int(np.ceil(w*n_individus))
		if count + n_offspring >= n_individus:
			n_offspring = n_individus - count
			offspring_per_couple.append(n_offspring)
			count += n_offspring
			pass
		else:
			count += n_offspring
			offspring_per_couple.append(n_offspring)
	return offspring_per_couple


def crossover(indiv1, indiv2, new_indiv):
	"""
	indiv1, indiv2 : Individus parents
	new_indiv : Enfant
	On prend une partie des genes du premier parent jusqu'a un point aleatoire, puis on prend
	les genes du 2e parent apres ce point.
	"""
	for i, layer_chromos in enumerate(new_indiv.chromos):
		for j, chromo in enumerate(layer_chromos):
			crossover_point = np.random.randint(len(chromo.genes)) # point ou l'on prend les genes de l'autre individu
			chromo.genes[:crossover_point] = indiv1.chromos[i][j].genes[:crossover_point]
			chromo.genes[crossover_point:] = indiv2.chromos[i][j].genes[crossover_point:]

	return new_indiv

def mutation(new_indiv, chance=0.25):

	# plusieurs choix d'implementation, mutation chromosome par chromosome ou sur un gene parmi tous
	# ici on fera chromosome par chromosome
	for layer_chromos in new_indiv.chromos:
		for chromo in layer_chromos:
			eps = np.random.rand()
			if eps < chance:
				gene_mutated = np.random.randint(len(chromo.genes))
				new_value = -gene_mutated
				chromo.genes[gene_mutated] = new_value

	return new_indiv

class Genetic:

	def __init__(self, n_individus, neural_structure, fit_function):
		self.n_individus = n_individus
		self.generations = [Population(n_individus, neural_structure, fit_function)]
		self.neural_structure = neural_structure
		self.fit_function = fit_function
		self.n_generations = 0
		self.model = self.__build_model__()

	# Une optimisation est possible en n'iterant qu'une fois sur chaque chromosome de l'individu
	# Cependant, selon l'implementation, on n'itere pas forcement a chaque etape sur tout les chromosomes
	# Nous preferons restes generalistes en perdant en temps de calcul


	def __build_model__(self):
		model = Sequential()
		model.add(Dense(self.neural_structure[1], input_dim=self.neural_structure[0], activation='softmax'))
		if len(self.neural_structure) > 2:
			for i, k in enumerate(self.neural_structure[2:-2]):
		 		model.add(Dense(k), activation='softmax')
			model.add(Dense(self.neural_structure[-1], activation='linear'))
		model.compile(optimizer='sgd', loss='mean_squared_error')
		return model

	def generate_indivs(self, couple, mutation_chance=0.25):
		new_indiv = Individu(self.neural_structure, self.fit_function) # on prend le meme individu que le meilleur parent
		new_indiv = crossover(couple[0], couple[1], new_indiv)
		new_indiv = mutation(new_indiv, chance=mutation_chance)
		return new_indiv


	def train(self, n_bests=2, weights=None, mutation_chance=0.25):
		if n_bests < 2:
			n_bests = 2
		current_gen = self.generations[-1] # derniere generation
		print("Fit population")
		current_gen.fit(self.model)
		print("Fit ended")
		fitness_ranks = np.array(current_gen.rank_fitness())
		n_fittest = np.array(current_gen.individuals)[fitness_ranks[:n_bests]]
		parents = [i for i in combinations(n_fittest[:n_bests], 2)] # toutes les paires possibles de parents, sans 2 fois le meme
		# la paire avec les meilleures parents est la premiere paire, puis qualite decroissante
		
		if not weights or len(weights) != n_bests:
			weights = np.ones(n_bests)	
		weights_per_couple = get_weights_per_couple(weights, n_bests)
		offspring_per_couple = get_offspring_per_couple(weights_per_couple, self.n_individus)
		new_gen = []
		for i, couple in enumerate(parents):
			offsprings = []
			for j in range(offspring_per_couple[i]):
				new = Individu(self.neural_structure, self.fit_function)

				offsprings.append(self.generate_indivs(couple, mutation_chance=mutation_chance))
			new_gen += offsprings
		new_pop = Population(self.n_individus, self.neural_structure, self.fit_function, individuals=new_gen)
		
		self.generations.append(new_pop)
		self.n_generations += 1
		return self.generations[-1]

	def save_gen(self, filename):
		file = h5py.File(filename, 'w')
		weights = []
		for i in range(self.n_individus):
			
			weights.append(np.array(self.generations[-1].individuals[i].weights))
		weights = np.array(weights, dtype=float)
		print(weights)
		file.create_dataset(name='weights', data=weights)
		file.flush()
		file.close()

	def load_gen(filename):
		file = h5py.File(filename, 'a')
		group = file['weights']
		weights = group['weights']
		file.close()
		return weights


def main():

	def fit(indi):
		return np.sum(indi.chromos[0][0].genes)

	neural_structure = [4,3]
	#print(neural_structure)
	init_chromo = generate_chromos_from_struct(neural_structure)
	print(init_chromo)
	weights = chromo_to_weights(init_chromo)
	#print(weights)
	conv_chromo = np.array(weights_to_chromos(weights))
	print(conv_chromo)
	conv_weights = np.array(chromo_to_weights(conv_chromo))
	#print(conv_weights)
	

if __name__== "__main__":
	main()