from pcdet.models.dense_heads.bev_feature_extractor_v2 import BEVFeatureExtractorV2
from .detector3d_template_v2 import Detector3DTemplateV2
import numpy as np

class CenterPoint_PointPillar_RCNNV2(Detector3DTemplateV2):
    def __init__(self, model_cfg, num_class, dataset):
        super().__init__(model_cfg=model_cfg, num_class=num_class, dataset=dataset)
        self.module_list = self.build_networks()

    def forward(self, batch_dict):
        batch_dict['spatial_features_stride']=1
        for cur_module in self.module_list:
            if str(cur_module) == "BEVFeatureExtractorV2()" or str(cur_module) == "PVRCNNHead()":
                pred_dicts, _ = self.post_processing_for_refine(batch_dict)
                rois, roi_scores, roi_labels = self.reorder_rois_for_refining(batch_dict['batch_size'], pred_dicts)
                batch_dict['rois'] = rois
                batch_dict['roi_scores'] = roi_scores
                batch_dict['roi_labels'] = roi_labels
                batch_dict['has_class_labels'] = True
                #batch_dict['final_predict'] = pred_dicts
            batch_dict = cur_module(batch_dict)
            

        
        # if True:
        #     for batch in range(batch_dict['gt_boxes'].squeeze(0).cpu().detach().numpy().shape[0]):
        #         gt_=[]
        #         #for GT box visualization in forward 
        #         # where, xyz,lwh,heading
        #         gt_box = batch_dict['gt_boxes'].squeeze(0).cpu().detach().numpy()[batch]
        #         #gt_box = [[gt_box[0][3], gt_box[0][4], gt_box[0][5]], gt_box[0][6], [gt_box[0][0], gt_box[0][1], gt_box[0][2]]] 
        #         points = batch_dict['points'].cpu().detach().numpy()
        #         pc_mask = (points[:, 0] == float(batch))
        #         points = points[pc_mask]
        #         np.save("/home/changwon/detection_task/SSOD/kakao/my_ssda_2/vis_in_model/pc/{}.npy".format(batch_dict['frame_id'][batch].item().split(".")[0]), points)
        #         file = open("/home/changwon/detection_task/SSOD/kakao/my_ssda_2/vis_in_model/box/{}.txt".format(batch_dict['frame_id'][batch].item().split(".")[0]), "w")
        #         with open("/home/changwon/detection_task/SSOD/kakao/my_ssda_2/vis_in_model/box/{}.txt".format(batch_dict['frame_id'][batch].item().split(".")[0]), "w") as f:
        #             for num in range(gt_box.shape[0]):
        #                 f.writelines("{},{},{},{},{},{},{},".format(gt_box[num][3],gt_box[num][4],gt_box[num][5],gt_box[num][6],gt_box[num][0],gt_box[num][1],gt_box[num][2]))
        #                 gt_.append([gt_box[num][3],gt_box[num][4],gt_box[num][5],gt_box[num][6],gt_box[num][0],gt_box[num][1],gt_box[num][2]])
                
        #         pred_box = batch_dict['batch_box_preds'].squeeze(0).cpu().detach().numpy()[batch]
        #         with open("/home/changwon/detection_task/SSOD/kakao/my_ssda_2/vis_in_model/box/pred_{}.txt".format(batch_dict['frame_id'][batch].item().split(".")[0]), "w") as f:
        #             for num in range(pred_box.shape[0]):
        #                 f.writelines("{},{},{},{},{},{},{},".format(pred_box[num][3],pred_box[num][4],pred_box[num][5],pred_box[num][6],pred_box[num][0],pred_box[num][1],pred_box[num][2]))
        #                 gt_.append([pred_box[num][3],pred_box[num][4],pred_box[num][5],pred_box[num][6],pred_box[num][0],pred_box[num][1],pred_box[num][2]])
        #         #scene_viz(gt_box, points)
        #         #token = batch_dict['metadata'][0]['token']
        #         print(batch_dict['frame_id'][batch].item().split(".")[0])

        if self.training:
            loss, tb_dict, disp_dict = self.get_training_loss()

            ret_dict = {
                'loss': loss
            }
            return ret_dict, tb_dict, disp_dict
        else:
            #pred_dicts, recall_dicts = self.post_processing(batch_dict)
            #pred_dicts, recall_dicts = self.post_processing_for_roi(batch_dict) #for roi head #
            pred_dicts = self.post_process(batch_dict) #test 1025
            rois, roi_scores, roi_labels = self.reorder_rois_for_refining(batch_dict['batch_size'], pred_dicts)
            batch_dict['rois'] = rois
            #batch_dict['roi_scores'] = roi_scores
            batch_dict['roi_labels'] = roi_labels
            batch_dict['has_class_labels'] = True
            pred_dicts, recall_dicts = self.post_processing_for_roi__(batch_dict)

            return pred_dicts, recall_dicts

    def get_training_loss(self):
        disp_dict = {}

        loss_rpn, tb_dict = self.dense_head.get_loss()
        loss_rcnn, tb_dict = self.roi_head.get_loss(tb_dict)
        loss = loss_rpn + loss_rcnn

        if self.backbone_2d.use_domain_cls:
            loss_domain, tb_dict = self.backbone_2d.get_loss(tb_dict)
            loss = loss + loss_domain

        return loss, tb_dict, disp_dict