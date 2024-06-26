from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os

# Define a blueprint for model requests
def model_blueprint(mysql):
    model_blueprint = Blueprint('model', __name__)

    # Directory to store model files
    model_file_path = '/home/ec2-user/stock_models/'

    # Route for adding a model
    @model_blueprint.route('/add', methods=['POST'])
    @jwt_required()  # Requires authentication
    def add_model():
        print("Adding a model")
        print(request.form)
        print(request.files)
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"error": "User ID not found in token"}), 401



        #Extract model details from the JSON data
        name = request.form.get('name')
        description = request.form.get('description')
        tags = request.form.getlist('tags')  # Assuming tags is a list of tag IDs



        #Extract the model file from the files parameter
        model_file = request.files.get('model_file')
        if not model_file :
            return jsonify({"error": "Model name and file are required"}), 400



        try:

            

            cur = mysql.connection.cursor()


            model_file_path_to_save = f"{model_file_path}{current_user_id}_{name}"


            # Insert the model details into the database
            cur.execute("INSERT INTO Models (UserID, Name, Description, Model_File_Path) VALUES (%s, %s, %s, %s)",
                        (current_user_id, name, description, model_file_path_to_save))
            model_id = cur.lastrowid

            #Save the model file to the specified directory
            print("Opened the file")
            model_file.save(model_file_path_to_save)
            print("Saved the model")

            # Insert tags for the model into the Model_Tags table
            for tag_id in tags:
                cur.execute("INSERT INTO Model_Tags (Model_ID, TagID) VALUES (%s, %s)", (model_id, tag_id))

            mysql.connection.commit()
            return jsonify({"message": "Model added successfully", "model_id": model_id}), 201
        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": "Failed to add model", "details": str(e)}), 500
        finally:
            cur.close()
    


    #Route for adding model img
    @model_blueprint.route('/update_model_imgURL', methods=['POST'])
    @jwt_required()  # Requires authentication
    def update_imgURL():
        print("Updating imgURL for a model")
        print(request.form)
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"error": "User ID not found in token"}), 401
        
        # Extract model details from the JSON data
        model_id = request.form.get('model_id')
        img_url = request.form.get('imgUrl')
        if not model_id or not img_url:
            return jsonify({"error": "Model ID and imgURL are required"}), 400
        
        try:
            cur = mysql.connection.cursor()
            
            # Update the imgURL in the database
            cur.execute("UPDATE Models SET imgURL = %s WHERE Model_ID = %s AND UserID = %s",
                        (img_url, model_id, current_user_id))
            if cur.rowcount == 0:
                return jsonify({"error": "Model not found or you don't have permission to update"}), 404
            
            mysql.connection.commit()
            return jsonify({"message": "imgURL updated successfully"}), 200
        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": "Failed to update imgURL", "details": str(e)}), 500
        finally:
            cur.close()

    
    @model_blueprint.route('/delete/<int:model_id>', methods=['DELETE'])
    @jwt_required()  # Requires authentication
    def delete_model(model_id):
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"error": "User ID not found in token"}), 401

        cur = mysql.connection.cursor()
        try:
            # Check if the model belongs to the current user
            cur.execute("SELECT UserID, Model_File_Path FROM Models WHERE Model_ID = %s", (model_id,))
            model = cur.fetchone()
            if not model or model['UserID'] != current_user_id:
                return jsonify({"error": "Model not found or user does not have permission to delete"}), 404
            
            # Delete the model file from the directory
            model_file_path = model['Model_File_Path']

            
            

            print(model_file_path)
            print(model_id)
            # Delete the model record from the database
            cur.execute("DELETE FROM Models WHERE Model_ID = %s", (model_id,))
            mysql.connection.commit()

            #Once succesfully deleted from db , remove the actual file
            if os.path.exists(model_file_path):
                os.remove(model_file_path)
                print(f"{model_file_path} has been removed successfully.")
            else:
                print(f"The file {model_file_path} does not exist.")

            
            return jsonify({"message": "Model deleted successfully"}), 200
        except Exception as e:
            mysql.connection.rollback()
            return jsonify({"error": "Failed to delete model", "details": str(e)}), 500
        finally:
            cur.close()
        


    # Route for fetching models by user ID
    @model_blueprint.route('/model_by_user', methods=['GET'])
    @jwt_required()  # Requires authentication
    def get_models_by_user_id():
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"error": "User ID not found in token"}), 401
        print("I am here ")
        cur = mysql.connection.cursor()
        try:
            # Fetch models belonging to the current user
            cur.execute("SELECT * FROM Models WHERE UserID = %s", (current_user_id,))
            models = cur.fetchall()
            return jsonify({"models": models}), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch models by user ID", "details": str(e)}), 500
        finally:
            cur.close()
    
    # Route for fetching models by tags
    @model_blueprint.route('/model_by_tags', methods=['GET'])
    def get_models_by_tags():
        tags = request.json.get('tags')  # Assuming tags are provided as JSON
        if not tags:
            return jsonify({"error": "At least one tag must be provided"}), 400

        cur = mysql.connection.cursor()
        try:
            # Fetch models associated with all provided tags
            cur.execute("""
                SELECT m.*
                FROM Models m
                JOIN Model_Tags mt ON m.Model_ID = mt.Model_ID
                WHERE mt.TagID IN %s
                GROUP BY m.Model_ID
                HAVING COUNT(DISTINCT mt.TagID) = %s
            """, (tuple(tags), len(tags)))
            models = cur.fetchall()
            return jsonify({"models": models}), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch models by tags", "details": str(e)}), 500
        finally:
            cur.close()

    # Other routes as needed...


    
    @model_blueprint.route('/get_all_models', methods=['GET'])
    @jwt_required()  # Requires authentication
    def get_all_models():
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"error": "User ID not found in token"}), 401
        
        cur = mysql.connection.cursor()
        try:
            # Fetch all models
            cur.execute("SELECT * FROM Models")
            models = cur.fetchall()
            return jsonify({"models": models}), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch all models", "details": str(e)}), 500
        finally:
            cur.close()

    # Route for fetching a model by model ID
    @model_blueprint.route('/get_model_by_id/<int:model_id>', methods=['GET'])
    @jwt_required()  # Requires authentication
    def get_model_by_id(model_id):
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"error": "User ID not found in token"}), 401

        

        
        cur = mysql.connection.cursor()
        try:
            # Fetch the model by ID
            cur.execute("SELECT * FROM Models WHERE Model_ID = %s and  UserID = %s", (model_id,current_user_id ,))
            model = cur.fetchone()
            if not model:
                return jsonify({"error": "Model not found"}), 404
            return jsonify({"model": model}), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch model by ID", "details": str(e)}), 500
        finally:
            cur.close()
    
    return model_blueprint
