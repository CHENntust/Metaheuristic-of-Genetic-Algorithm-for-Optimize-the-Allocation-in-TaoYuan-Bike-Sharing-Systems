# -*- coding: utf-8 -*-
import csv,sqlite3,random,datetime,sys
import matplotlib.pyplot as plt
import pandas as pd

global history_opt_sol
history_opt_sol = {'x':[],'y':[]}

#for sorting multi-dimension list
def sort_principle(element):
    return element[0]

class Station():
    """
    < attribute >
        self.capacity : A distriction of total car which stay in this station
        self.remain : To record the current number of vehicles on the site
    < method >
        get_capacity : return capacity of this station
        set_amount : To record the amount of assignment of vehicle
        fix : To access remaining car in this station
    """
    def __init__(self,capacity):
        self.capacity = capacity
        self.remain = None
        
    def get_capacity(self):
        return self.capacity
    
    def set_amount(self,amount):
        self.remain = amount
        
    def fix(self,num):
        temp_value = self.remain + num
        if temp_value >= 0:#設要停車的人會等到有人來騎車，因此temp_value <= self.capacity
            self.remain += num
            return True
        else:
            return False
        
#object for ubike system.
class Ubike_System():
    """
    < attribute >
        self.stations : Objects of each stations. 
    < method >
        init_stations: setting objects of each station.
        get_capacitys : get capacities of each station.
        Allocation : computing total time of established transaction by allocation.
        Data_Filter: obtain transactions record of which in a prticular moment and shift
    """
    def __init__(self):
        self.stations = self.init_stations()
    
    def init_stations(self):
        stations = {}
        with open('Capacity for each station.csv','r',encoding="utf-8") as f:
            rows = csv.reader(f)
            for row in rows:
                if row[0] != "\ufeffstation":
                    name, capacity = row[0], int(float(row[1]))
                    stations.setdefault(row[0],Station(capacity))
        return stations
        
    def Get_capacitys(self):
        capacity_dict = {}
        for i in self.stations:
            capacity_dict.setdefault(i,self.stations[i].get_capacity())
        return capacity_dict
    
    def Allocate(self,date,shift,Allocation):
        #設置各站點的分配量
        for i in Allocation:
            self.stations[i].set_amount(Allocation[i])
        #以堆疊依序配置進出數量
        training_data = self.Data_Filter(date,shift)
        training_data.sort()
        stacks = []
            
        for i in training_data:
            date,time,time1 = i[0].split('/'),i[1].split(':'),i[4].split(':')
            start_stamp = datetime.datetime(int(date[0]),int(date[1]),int(date[2]),int(time[0]),int(time[1]),int(time[2]))
            start_stamp1 = datetime.datetime(int(date[0]),int(date[1]),int(date[2]),int(time1[0]),int(time1[1]),int(time1[2]))
            
            end_stamp = datetime.datetime(int(date[0]),int(date[1]),int(date[2]),23,59,59)
            diff_second = (end_stamp - start_stamp).seconds
            diff_used = (start_stamp1 - start_stamp).seconds
            stacks.append([diff_second,'MOSI',i[1],i[2],diff_used])

            end_stamp1 = datetime.datetime(int(date[0]),int(date[1]),int(date[2]),23,59,59)
            diff_second1 = (end_stamp1 - start_stamp1).seconds
            stacks.append([diff_second1,'MISO',i[4],i[5],0])
        stacks.sort(reverse=True)
        standard_data = {}
        for i in stacks:
            if i[1] == 'MOSI':#本站出去,數量-1,成交時數1
                try:
                    standard_data[i[3]].append([-1,i[4]])
                except:
                    standard_data.setdefault(i[3],[[-1,i[4]]])
            elif i[1] == 'MISO': #進站,數量+1,成交時數0
                try:
                    standard_data[i[3]].append([1,i[4]])
                except:
                    standard_data.setdefault(i[3],[[1,i[4]]])
                    
        deal_time,invalid_time = 0,0
        for i in standard_data:
            for j in standard_data[i]:
                try:
                    status = self.stations[i].fix(j[0])
                    if status == True:
                        deal_time += j[1]
                    else:
                        invalid_time += j[1]
                        pass
                except:
                    pass
        return(deal_time)
        
    def Data_Filter(self,date,shift):
        conn = sqlite3.connect('DB.db')
        c = conn.cursor()
        cursor = c.execute("SELECT * from  record WHERE start_date = '"+date+"'").fetchall()
        temp_data = []
        for i in cursor:
            date,time= i[0].split('/'),i[1].split(':')
            start_stamp = datetime.datetime(int(date[0]),int(date[1]),int(date[2]),int(time[0]),int(time[1]),int(time[2]))
            end_stamp = datetime.datetime(int(date[0]),int(date[1]),int(date[2]),23,59,59)
            diff_hour = ((end_stamp - start_stamp).seconds)/(3600)
            if shift == 1:
                if diff_hour >16: #0~8
                    temp_data.append(i)
            elif shift == 2:
                if diff_hour >=8 and diff_hour >16: #8~16
                    temp_data.append(i)
            else:
                if diff_hour <=8:  #16~24
                    temp_data.append(i)
        conn.close()
        return temp_data
  
    
class GA():
    """
    < attribute > 
        self.init_date : setting start date.
        self.pop ： setting population size.
        self.crossover_rate : setting crossover rate.
        self.mutation_rate : setting mutation rate.
        self.start_point_for_each_week ： recording a timestamp of each week. 
        self.Ubike_System : Object of the Ubike System 
        self.gen_index : current iteration number. 
        self.period : recording total shift of each week 
        self.population : recording chromosomes 
        self.Archive :  recording chromosomes which are non-dominated in history. 
        self.Plot : for visualization. 
        self.Archive_Plot : for visualization. 
        self.gold_r : peremeter of selection weight. 
        self.history_CP : for visualization. 
    < method > 
        init_allocation : set initial population 
        fit : the process of each generation 
        reset_period :obtain total shift of each week in current timestamp. 
        crossover_and_mutation: transfer the chromosome into binery representation and conduct crossover and mutation 
        show_plot : for visualization. 
    """
    def __init__(self,Ubike_System,start_time,pop_num = 2, generation = 1000, crossover_rate = 0.95, mutation_rate = 0.4):
        self.init_date = start_time
        self.pop = pop_num
        self.start_point_for_each_week = self.init_date
        self.Ubike_System = Ubike_System
        self.gen_index = 0
        self.period = None
        
        self.population = self.init_allocation(self.pop)
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.Archive = []
        self.Plot = []
        self.Archive_Plot = {'x':[],'y':[]}
        self.gold_r = 1.618
        self.history_CP = []
        self.fit(generation)
        
    def reset_period(self):
        #回傳單筆chromosome包含的時間表，以計算成立出租時間。
        date,shift = self.start_point_for_each_week,1
        period = []
        d = date.split('/')
        date = str(datetime.datetime(int(d[0]), int(d[1]), int(d[2])) + datetime.timedelta(days=7*0))[:10]
        date = date.replace('-','/')
        period = []
        d = date.split('/')
        for i in range(8):
            for j in range(3):
                temp_date = str(datetime.datetime(int(d[0]), int(d[1]), int(d[2])) + datetime.timedelta(days=i))[:10]
                temp_date = temp_date.replace('-','/')
                period.append([temp_date,j+1])
        return period
            
        
    def init_allocation(self,pop_num):
        population = []
        random.seed(20)
        for z in range(pop_num):
            caps = self.Ubike_System.Get_capacitys()
            all_allocations = []
            for week in range(21):
                Allocations = {}
                for i in caps:
                    Allocations.setdefault(i,random.randrange(0,caps[i]))
                all_allocations.append(Allocations)
            population.append(all_allocations)
        return population
    
    def fit(self,generation):
     	    for round_n in range(10):
            for i in range(generation):
                print('------【generation',i,'】------')
                objective_space = {}
                
                for chromosome in self.population:
                    self.start_point_for_each_week = self.init_date
                    fitness,amount = 0,0
                    for period_temp in range(26):
                        print(self.start_point_for_each_week)
                        self.period = self.reset_period()
                        for period_index in range(len(self.period)):
                            if period_index <= 20:
                                #print(self.period[period_index][0])
                                fitness += self.Ubike_System.Allocate(self.period[period_index][0],self.period[period_index][1],chromosome[period_index])
                                temp = 0
                                for station in chromosome[period_index]:
                                    temp += chromosome[period_index][station]
                                if temp > amount:
                                    amount = temp
                            else:
                                self.start_point_for_each_week = self.period[period_index][0]
                    objective_space[amount] = objective_space.get(amount,0)+fitness
                        
                print('')
                bucket = []
                remaining_sol_amount = len(self.population)
                self.Plot.append({'x':list(objective_space.keys()),'y':list(objective_space.values())})
                nondominated_chromosome,nondominated_index,dominated_index = [],[],[]
                count = 0 
                for X in objective_space:
                    non_dominated = True
                    for X2 in objective_space:
                        if X != X2:
                            if X > X2 and objective_space[X] < objective_space[X2]:
                                non_dominated = False
                    if non_dominated == True:
                        nondominated_index.append(count)
                        print('>> chromosome',count,' are non-dominated',[X,objective_space[X]])
                        self.Archive.append([X,objective_space[X],self.population[count]])
                        nondominated_chromosome.append(self.population[count])
                    else:
                        dominated_index.append(count)
                    count += 1
    
                print(' ')
                print('將non-dominated的Archive基因('+str(len(nondominated_chromosome))+'個)加入Archive')
                archive_num = int(self.gold_r*remaining_sol_amount)
                remaining_sol_amount -= len(nondominated_chromosome)
                print(' ')
                cal_temp = 2
                archive_num_opt = 0
                #archive_num = 0
                while True:
                    space_key = {}
                    temp_space = {}
                    v_index = 0
                    r_index  = 0
                    for volumn in objective_space:
                        if v_index in dominated_index:
                            space_key.setdefault(r_index,v_index)
                            r_index += 1
                            temp_space.setdefault(volumn,objective_space[volumn])
                        v_index  += 1
                
                    nondominated_chromosome,nondominated_index,dominated_index = [],[],[]
                    count = 0 
                    for o1 in temp_space:
                        non_dominated = True
                        for o2 in temp_space:
                            if o1 != o2:
                                if o1 > o2 and temp_space[o1] < temp_space[o2]:
                                    non_dominated = False
                                    
                        if non_dominated == True:
                            nondominated_index.append(space_key[count])
                            nondominated_chromosome.append(self.population[space_key[count]])
                        else:
                            dominated_index.append(space_key[count])
                            
                        count += 1
                    for temp_ind in range(int(self.gold_r*remaining_sol_amount)):
                        for temp_c in nondominated_chromosome:
                            #print(temp_c)
                            bucket.append(temp_c)
                    print('將第',cal_temp,'層parato front的基因('+str(len(nondominated_chromosome))+'個)加入bucket',str(int(self.gold_r*remaining_sol_amount)),'次')
                    if cal_temp == 2:
                        archive_num_opt = int(self.gold_r*remaining_sol_amount)
                    #if cal_temp == 2:
                        #archive_num = int(self.gold_r*remaining_sol_amount)
                    cal_temp += 1
                    remaining_sol_amount -= len(nondominated_chromosome)
                    if len(nondominated_index) <=0 or remaining_sol_amount<=0:
                        break
                
                ind_delete = 0
                new_a =[]
                napx,napy=[],[]
                for opt in self.Archive:
                    non_dominated = True
                    for opt2 in self.Archive:
                        if opt != opt2:
                            if opt[0] > opt2[0] and opt[1] < opt2[1]:
                                non_dominated = False
                    if non_dominated == True:
                        new_a.append(opt)
                        napx.append(opt[0])
                        napy.append(opt[1])
                    ind_delete += 1
                self.Archive = new_a
                self.Archive_Plot['x'] = napx
                self.Archive_Plot['y'] = napy
                    
                for x in self.Archive:
                    #for zxc in range(int(self.gold_r*len(self.population))):
                    for jhj in range(archive_num):
                        bucket.append(x[2])
                print('')
                print('將Archive的基因('+str(len(self.Archive))+'個)加入bucket',str(archive_num),'次')
                if i > 0:
                    for qweq in range(archive_num_opt):
                        bucket.append(max_archive[2])
                print('將歷史前緣最佳的Archive基因(1個)加入bucket',archive_num_opt,'次')
                print('')        
                
                new_population = []
                for temp in range(int(len(self.population)/2)):
                    while True:
                        selections = random.sample(bucket,2)
                        if selections[0] != selections[1]:
                            break
                    new_c1,new_c2={},{}
                    result1,result2 = self.crossover_mutation(selections[0],selections[1],self.crossover_rate,self.mutation_rate)
    
                    new_population.append(result1)
                    new_population.append(result2)
                self.Archive.sort(key =sort_principle)
                
                max_CP = 0
                for temp_index in range(len(self.Archive)):
                    temp_CP = 0
                    if self.Archive[temp_index][0] == 0 :
                        temp_CP = 0
                    else:
                        temp_CP = self.Archive[temp_index][1]/self.Archive[temp_index][0]
                    if temp_CP > max_CP:
                        max_archive = self.Archive[temp_index]
                        max_CP = temp_CP
                        
                self.population = new_population
                self.show_plot(self.gen_index,max_archive[0],max_archive[1],round_n,'X_'+str(max_archive[0])+',T_'+str(max_archive[1]))
                self.gen_index += 1
                
                temp_index = 0 
                for day in range(7):
                    for shif in range(3):
                        print('d'+str(day+1)+'_'+str(shif+1)+' = ',max_archive[2][temp_index])
                        temp_index += 1
                print(objective_space)
                print('opt sol X_',max_archive[0],',T_',max_archive[1])
                print('C/P:',max_CP)
                self.history_CP.append(max_CP)
                
                plt.style.use('ggplot')
                fig = plt.figure(figsize=[6,2])
                ax = plt.subplot(111)
                ax.plot(self.history_CP,c='red')
                ax.set_xlabel('generation')
                ax.set_ylabel('C/P value')
                ax.set_title('History of optimal C/P value')
                fig.savefig('test'+str(round_n+1)+'/History_CP value.png')
                plt.close('all')
            self.start_point_for_each_week = self.init_date
            self.Ubike_System = Ubike_System()
            self.gen_index = 0
            self.period = None
        
            self.population = self.init_allocation(self.pop)

    def crossover_mutation(self,chromosome1,chromosome2,r1,r2):
        t1,t2 = chromosome1,chromosome2
        caps = self.Ubike_System.Get_capacitys()
        new_c1,new_c2= [],[] 
        if random.random() < r1 :
            for shift in range(len(chromosome1)):
                temp_shift1 = {}
                temp_shift2 = {}
                for station in chromosome1[shift]:
                    a = chromosome1[shift][station]
                    try:
                        b = chromosome2[shift][station]
                    except:
                        b = 0
                    max_len = len(str(bin(caps[station]))[2:])
                    data1 = str(bin(a))[2:]
                    data2 = str(bin(b))[2:]
                    
                    while True:
                        if len(data1) < max_len:
                            data1 = '0'+data1
                        else:
                            break
                    while True:
                        if len(data2) < max_len:
                            data2 = '0'+data2
                        else:
                            break
                    total_len = max_len-1
                    while True:
                        segment_point = random.randint(1,total_len+1)
                        
                        d1,d2 = data1[:segment_point],data1[segment_point:]
                        d3,d4 = data2[:segment_point],data2[segment_point:]
                        
                        data1 = d1+d4
                        data2 = d3+d2
                        if int(data1,2) <= caps[station] and int(data2,2) <= caps[station]:
                            break
                    temp_shift1[station] = int(data1,2)
                    temp_shift2[station] = int(data2,2)
                new_c1.append(temp_shift1)
                new_c2.append(temp_shift2)
            chromosome1,chromosome2 = new_c1,new_c2
        new_c1,new_c2 = [],[]
        if random.random() < r2:
            for shift in range(len(chromosome1)):
                temp_shift1 = {}
                temp_shift2 = {}
                for station in chromosome1[shift]:
                    a = chromosome1[shift][station]
                    b = chromosome2[shift][station]
                    max_len = len(str(bin(caps[station]))[2:])
                    data1 = str(bin(a))[2:]
                    data2 = str(bin(b))[2:]
                    
                    while True:
                        if len(data1) < max_len:
                            data1 = '0'+data1
                        else:
                            break
                    while True:
                        if len(data2) < max_len:
                            data2 = '0'+data2
                        else:
                            break
                    
                    max_len = len(str(bin(caps[station]))[2:])
                    total_len = max_len-1

                    while True:
                        mutate_point = random.randint(1,total_len+1)
                        if len(data1) > 1:
                            if data1[mutate_point-1] == '0':
                                data1 = data1[:mutate_point-1]+'1'+data1[mutate_point:]
                            else:
                                data1 = data1[:mutate_point-1]+'0'+data1[mutate_point:]
                        else:
                            if data1 == '0':
                                data1 = '1'
                            else:
                                data1 = '0'
                        if int(data1,2) <= caps[station] and int(data2,2) <= caps[station]:
                            break
                    while True:
                        mutate_point = random.randint(1,total_len+1)
                        if len(data1) > 1:
                            if data2[mutate_point-1] == '0':
                                data2 = data2[:mutate_point-1]+'1'+data2[mutate_point:]
                            else:
                                data2 = data2[:mutate_point-1]+'0'+data2[mutate_point:]
                        else:
                            if data2 == '0':
                                data2 = '1'
                            else:
                                data2 = '0'
                        if int(data1,2) <= caps[station] and int(data2,2) <= caps[station]:
                            break

                    temp_shift1[station] = int(data1,2)
                    temp_shift2[station] = int(data2,2)
                new_c1.append(temp_shift1)
                new_c2.append(temp_shift2)
            chromosome1,chromosome2 = new_c1,new_c2
        return chromosome1,chromosome2
    
    def show_plot(self,g,rx,ry,round_n,xy):
        index = 0
        for ip in self.Plot:
            if index >=g:
                plt.style.use('ggplot')
                fig = plt.figure(figsize=[7,5])
                ax = plt.subplot(111)
                ax.scatter(ip['x'],ip['y'],c='tab:blue',label='dominated sol.')
                ax.scatter(self.Archive_Plot['x'],self.Archive_Plot['y'],c = 'orange',label='non-dominated sol.')
                ax.scatter([rx],[ry],c = 'red',label='optimal sol.')
                ax.set_xlabel('the number of bikes')
                ax.set_ylabel('the total using time of bikes')
                ax.set_title('Objective space')
                plt.legend(loc='center left',bbox_to_anchor=(1.,0.9))
                plt.tight_layout()
                fig.savefig('test'+str(round_n+1)+'/generation_'+str(index)+"_"+xy+'.png')
                plt.close('all')
                global history_opt_sol
                history_opt_sol['x'].append(rx)
                history_opt_sol['y'].append(ry)
                plt.style.use('ggplot')
                fig = plt.figure(figsize=[7,5])
                ax = plt.subplot(111)
                ax.scatter(history_opt_sol['x'],history_opt_sol['y'],c = 'red',label='optimal sol.')
                ax.set_xlabel('the number of bikes')
                ax.set_ylabel('the total using time of bikes')
                ax.set_title('History of optimal sol.')
                plt.legend(loc='center left',bbox_to_anchor=(1.,0.9))
                plt.tight_layout()
                fig.savefig('test'+str(round_n+1)+'/opt_'+str(index)+"_"+xy+'.png')
                plt.close('all')
                
            index += 1
            
decision = GA(Ubike_System(),'2018/01/01')
decision
