import utils
import random

MAX_ROUND = 10

if __name__ == '__main__':
    G = utils.create_network_topo_with_old_flows()
    flowinfo = utils.get_flowinfo()
    CL = utils.search_potential_congested_links()
    global_D = utils.create_dependency_graph(utils.get_dependency(CL))
    utils.update_alone_nodes(G, global_D)

    transition_info = {}
    for CNid in global_D.nodes():
        for nf_dict in utils.map_id_to_CN(CNid):
            nf, fid = utils.dict2tuple(nf_dict)
            if not transition_info.has_key(fid):
                transition_info[fid] = {nf: flowinfo[fid]}
            else:
                transition_info[fid].update({nf: flowinfo[fid]})

    tmp_result = {}
    rest_nf = None
    shield = []

    count = 0
    while True:
        count += 1
        print 'Round', count
        tmp_result[count] = []

        split_D = utils.split_dependency_graph(global_D)
        for D in split_D:

            US = []

            # update without deadlocks:
            US_ = []
            step1_flag = False

            CNids_with_no_outdegree = map(lambda i: i[0], filter(lambda i: i[1] == 0, D.out_degree()))

            for CNid in CNids_with_no_outdegree:
                nf_list = utils.map_id_to_CN(CNid)

                for i in xrange(len(nf_list)):
                    nf_dict = nf_list[i]

                    if utils.has_dependency(D, nf_dict):
                        continue

                    nf, fid = utils.dict2tuple(nf_dict)

                    if utils.can_update_in_segment(G, fid, transition_info[fid][nf]):
                        utils.update_segment(G, fid, transition_info[fid][nf])
                        US_.append((nf_dict, transition_info[fid][nf]))
                        utils.remove_nf(global_D, nf_dict)
                        transition_info[fid][nf] = 0.0

            if US_:
                US += US_
                step1_flag = True

            # update in deadlock
            US_ = []
            step2_flag = False
            if not step1_flag:
                nf_list = utils.get_all_nf(D)

                record = []
                for nf_dict in nf_list:
                    nf, fid = utils.dict2tuple(nf_dict)
                    if utils.can_update_in_segment(G, fid, transition_info[fid][nf]):
                        record.append((nf_dict, transition_info[fid][nf]))

                record.sort(key=lambda x: x[1], reverse=True)

                for nf_dict, size in record:
                    nf, fid = utils.dict2tuple(nf_dict)
                    if utils.can_update_in_segment(G, fid, size):
                        utils.update_segment(G, fid, size)
                        US_.append((nf_dict, size))
                        utils.remove_nf(global_D, nf_dict)
                        transition_info[fid][nf] = 0.0

            if US_:
                US += US_
                step2_flag = True

            if US:
                print US
                tmp_result[count] += US

            # random shield
            if not step1_flag and not step2_flag:
                rest_nf = utils.get_all_nf(global_D)
                nf_dict = random.choice(rest_nf)
                nf, fid = utils.dict2tuple(nf_dict)

                utils.remove_nf(global_D, nf_dict)
                utils.remove_flow(G, fid, transition_info[fid][nf])
                shield.append((nf_dict, transition_info[fid][nf]))

                print 'shield:', (nf_dict, transition_info[fid][nf])
                tmp_result[count] = (nf_dict, transition_info[fid][nf])

        if not global_D.nodes() or count >= MAX_ROUND:
            break

    next_round = max(tmp_result.keys())+1
    tmp_result[next_round] = {}

    if global_D.nodes():
        tmp_result[next_round]['shield'] = []
        rest_nf = utils.get_all_nf(global_D)
        for nf_dict in rest_nf:
            utils.remove_nf(global_D, nf_dict)
            nf, fid = utils.dict2tuple(nf_dict)
            utils.remove_flow(G, fid, transition_info[fid][nf])
            shield.append((nf_dict, transition_info[fid][nf]))
            tmp_result[next_round]['shield'].append((nf_dict, transition_info[fid][nf]))

        print 'Round', next_round
        print 'shield:', tmp_result[next_round]['shield']

    if shield:
        tmp_result[next_round]['recover'] = []
        for nf_dict, size in shield:
            nf, fid = utils.dict2tuple(nf_dict)
            utils.recover_flow(G, fid, size)
            transition_info[fid][nf] = round(transition_info[fid][nf] - size, 2)
            tmp_result[next_round]['recover'].append((nf_dict, size))

        print 'Rocover'
        print shield

    result = {}
    for r in tmp_result:
        result[r] = []
        if type(tmp_result[r]) == list:
            for item in tmp_result[r]:
                result[r].append(item)
        elif type(tmp_result[r]) == tuple:
            result[r] = {'shield': tmp_result[r]}
        elif type(tmp_result[r]) == dict:
            result[r] = tmp_result[r]

    print
    print 'Round', '\t', 'State', '\t\t', 'Num', '\t', 'FlowSize'
    for r in result:
        print r, '\t',
        if type(result[r]) == list:
            print '\t\t', len(result[r]), '\t', sum([item[1] for item in result[r]])
        elif type(result[r]) == dict:
            if result[r].has_key('shield') and not result[r].has_key('recover'):
                print 'shield', '\t\t', 1, '\t', result[r]['shield'][1]
            elif result[r].has_key('shield') and result[r].has_key('recover'):
                print 'shield', '\t\t', len(result[r]['shield']), '\t', sum([item[1] for item in result[r]['shield']])
                print '\t', 'recover', '\t', len(result[r]['recover']), '\t', sum([item[1] for item in result[r]['recover']])

    print
    print 'update order:'
    print result

    complete_round_map = {}
    for fid in flowinfo:
        complete_round_map[fid] = 0

    for r in result:
        if type(result[r]) == list:
            for nf_tup in result[r]:
                nf, fid = utils.dict2tuple(nf_tup[0])
                complete_round_map[fid] = r
        elif type(result[r]) == dict:
            if result[r].has_key('recover'):
                for item in result[r]['recover']:
                    nf, fid = utils.dict2tuple(item[0])
                    complete_round_map[fid] = r

    utils.save_complete_round(complete_round_map)

    print
    print 'complete round:'
    print complete_round_map
